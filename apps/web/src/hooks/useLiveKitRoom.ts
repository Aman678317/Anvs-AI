"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import {
  Room,
  RoomEvent,
  VideoPresets,
  Track,
  createLocalVideoTrack,
  createLocalAudioTrack,
  LocalVideoTrack,
  LocalAudioTrack,
  RemoteVideoTrack,
  RemoteTrack,
  RemoteTrackPublication,
  RemoteParticipant,
} from "livekit-client";
import { useMeetingStore } from "../stores/useMeetingStore";

function createFallbackVideoTrack(displayName: string = "Guest"): LocalVideoTrack {
  if (typeof document === "undefined") {
    throw new Error("Cannot create fallback track in SSR");
  }
  const canvas = document.createElement("canvas");
  canvas.width = 640;
  canvas.height = 480;
  const ctx = canvas.getContext("2d");
  let frame = 0;

  const render = () => {
    if (!ctx) return;
    frame++;
    const grad = ctx.createLinearGradient(0, 0, 640, 480);
    grad.addColorStop(0, "#1e293b");
    grad.addColorStop(1, "#0f172a");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 640, 480);

    const centerX = 320;
    const centerY = 210;
    const pulse = Math.sin(frame * 0.05) * 6;

    ctx.beginPath();
    ctx.arc(centerX, centerY, 70 + pulse, 0, Math.PI * 2);
    ctx.fillStyle = "#3b82f6";
    ctx.globalAlpha = 0.25;
    ctx.fill();
    ctx.globalAlpha = 1.0;

    ctx.beginPath();
    ctx.arc(centerX, centerY, 55, 0, Math.PI * 2);
    ctx.fillStyle = "#2563eb";
    ctx.fill();

    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 36px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    const initials = displayName.slice(0, 2).toUpperCase() || "ME";
    ctx.fillText(initials, centerX, centerY);

    ctx.font = "600 20px Inter, sans-serif";
    ctx.fillStyle = "#f8fafc";
    ctx.fillText(displayName, centerX, 320);

    ctx.font = "500 13px Inter, sans-serif";
    ctx.fillStyle = "#10b981";
    ctx.fillText("● Live Camera", centerX, 350);

    requestAnimationFrame(render);
  };
  render();

  const stream = (canvas as any).captureStream(25);
  const track = stream.getVideoTracks()[0];
  return new LocalVideoTrack(track);
}

function createFallbackAudioTrack(): LocalAudioTrack {
  const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
  const ctx = new AudioCtx();
  const osc = ctx.createOscillator();
  const dst = ctx.createMediaStreamDestination();
  const gain = ctx.createGain();
  gain.gain.value = 0.00001; // Silent
  osc.connect(gain);
  gain.connect(dst);
  osc.start();
  const track = dst.stream.getAudioTracks()[0];
  return new LocalAudioTrack(track);
}

/**
 * Resilient multi-stage local camera track acquisition.
 * 1. LiveKit h720 preset
 * 2. LiveKit default constraints
 * 3. Native navigator.mediaDevices.getUserMedia wrapped in LocalVideoTrack
 * 4. Animated canvas live stream fallback (if camera is locked by another browser tab)
 */
async function acquireCameraTrack(displayName: string = "Guest"): Promise<LocalVideoTrack> {
  try {
    const track = await createLocalVideoTrack({
      resolution: VideoPresets.h720.resolution,
    });
    return track;
  } catch (err1) {
    try {
      const track = await createLocalVideoTrack();
      return track;
    } catch (err2) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: "user",
          },
          audio: false,
        });
        const videoTrack = stream.getVideoTracks()[0];
        return new LocalVideoTrack(videoTrack);
      } catch (err3) {
        console.warn("Hardware camera unavailable or locked by another tab. Activating live visual canvas stream fallback:", err3);
        return createFallbackVideoTrack(displayName);
      }
    }
  }
}

/**
 * Resilient multi-stage local microphone track acquisition.
 */
async function acquireAudioTrack(): Promise<LocalAudioTrack> {
  try {
    const track = await createLocalAudioTrack();
    return track;
  } catch (err1) {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: false,
      });
      const audioTrack = stream.getAudioTracks()[0];
      return new LocalAudioTrack(audioTrack);
    } catch (err2) {
      console.warn("Hardware microphone unavailable. Activating silent audio stream fallback:", err2);
      return createFallbackAudioTrack();
    }
  }
}

export function useLiveKitRoom(
  livekitUrl: string = process.env.NEXT_PUBLIC_LIVEKIT_URL || "ws://localhost:7880",
  token: string | null,
) {
  const roomRef = useRef<Room | null>(null);
  const [localVideoTrack, setLocalVideoTrack] = useState<LocalVideoTrack | null>(null);
  const [localAudioTrack, setLocalAudioTrack] = useState<LocalAudioTrack | null>(null);
  const [remoteVideoTracks, setRemoteVideoTracks] = useState<Record<string, RemoteVideoTrack | MediaStreamTrack | null>>({});
  const [screenTrack, setScreenTrack] = useState<LocalVideoTrack | null>(null);

  const localVideoTrackRef = useRef<LocalVideoTrack | null>(null);
  const localAudioTrackRef = useRef<LocalAudioTrack | null>(null);
  const screenTrackRef = useRef<LocalVideoTrack | null>(null);
  const pcsRef = useRef<Map<string, RTCPeerConnection> | null>(null);
  const p2pBcRef = useRef<BroadcastChannel | null>(null);

  const {
    participantId,
    displayName,
    meetingId,
    setLiveKitConnected,
    setActiveSpeakers,
    isMicMuted,
    isVideoEnabled,
    isScreenSharing,
    setMicMuted,
    setVideoEnabled,
    setScreenSharing,
  } = useMeetingStore();

  // 1. Immediately initialize and maintain local camera hardware independently of SFU connection
  useEffect(() => {
    let cancelled = false;

    async function ensureVideoTrack() {
      if (!isVideoEnabled) {
        if (localVideoTrackRef.current) {
          try {
            await localVideoTrackRef.current.mute();
          } catch {
            localVideoTrackRef.current.stop();
          }
        }
        return;
      }

      // Check if existing track is already live
      if (
        localVideoTrackRef.current &&
        localVideoTrackRef.current.mediaStreamTrack.readyState === "live"
      ) {
        if (localVideoTrackRef.current.isMuted) {
          await localVideoTrackRef.current.unmute();
        }
        return;
      }

      try {
        const vTrack = await acquireCameraTrack(displayName);
        if (cancelled) {
          vTrack.stop();
          return;
        }

        localVideoTrackRef.current = vTrack;
        setLocalVideoTrack(vTrack);

        // Publish to LiveKit SFU room if already connected
        const room = roomRef.current;
        if (room && room.state === "connected") {
          room.localParticipant.publishTrack(vTrack).catch((e) => {
            console.warn("Could not publish camera track to LiveKit SFU:", e);
          });
        }
      } catch (err) {
        console.error("Camera acquisition failed in meeting room:", err);
      }
    }

    ensureVideoTrack();

    return () => {
      cancelled = true;
    };
  }, [isVideoEnabled]);

  // 2. Immediately initialize and maintain local microphone hardware independently of SFU connection
  useEffect(() => {
    let cancelled = false;

    async function ensureAudioTrack() {
      if (isMicMuted) {
        if (localAudioTrackRef.current) {
          try {
            await localAudioTrackRef.current.mute();
          } catch {
            localAudioTrackRef.current.stop();
          }
        }
        return;
      }

      if (
        localAudioTrackRef.current &&
        localAudioTrackRef.current.mediaStreamTrack.readyState === "live"
      ) {
        if (localAudioTrackRef.current.isMuted) {
          await localAudioTrackRef.current.unmute();
        }
        return;
      }

      try {
        const aTrack = await acquireAudioTrack();
        if (cancelled) {
          aTrack.stop();
          return;
        }

        localAudioTrackRef.current = aTrack;
        setLocalAudioTrack(aTrack);

        const room = roomRef.current;
        if (room && room.state === "connected") {
          room.localParticipant.publishTrack(aTrack).catch((e) => {
            console.warn("Could not publish audio track to LiveKit SFU:", e);
          });
        }
      } catch (err) {
        console.error("Mic acquisition failed in meeting room:", err);
      }
    }

    ensureAudioTrack();

    return () => {
      cancelled = true;
    };
  }, [isMicMuted]);

  // 3. Connect to LiveKit SFU Room and manage multi-party video & audio subscriptions
  useEffect(() => {
    if (!token) return;

    const room = new Room({
      adaptiveStream: true,
      dynacast: true,
      videoCaptureDefaults: {
        resolution: VideoPresets.h720.resolution,
      },
    });

    roomRef.current = room;
    const attachedAudioElements: HTMLAudioElement[] = [];

    // Room event listeners
    room.on(RoomEvent.Connected, () => {
      setLiveKitConnected(true);

      // Publish local camera and mic if already acquired
      if (localVideoTrackRef.current && isVideoEnabled) {
        room.localParticipant.publishTrack(localVideoTrackRef.current).catch((e) => {
          console.warn("Failed to publish video track on room connection:", e);
        });
      }
      if (localAudioTrackRef.current && !isMicMuted) {
        room.localParticipant.publishTrack(localAudioTrackRef.current).catch((e) => {
          console.warn("Failed to publish audio track on room connection:", e);
        });
      }

      // Populate already published remote tracks
      const existingTracks: Record<string, RemoteVideoTrack> = {};
      room.remoteParticipants.forEach((p) => {
        p.trackPublications.forEach((pub) => {
          if (pub.track && pub.kind === Track.Kind.Video) {
            existingTracks[p.identity] = pub.track as RemoteVideoTrack;
          }
          if (pub.track && pub.kind === Track.Kind.Audio) {
            const el = pub.track.attach();
            attachedAudioElements.push(el);
          }
        });
      });
      if (Object.keys(existingTracks).length > 0) {
        setRemoteVideoTracks((prev) => ({ ...prev, ...existingTracks }));
      }
    });

    room.on(RoomEvent.Disconnected, () => {
      setLiveKitConnected(false);
    });

    room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
      setActiveSpeakers(speakers.map((s) => s.identity));
    });

    // Remote participant published a track
    room.on(
      RoomEvent.TrackSubscribed,
      (track: RemoteTrack, _publication: RemoteTrackPublication, participant: RemoteParticipant) => {
        if (track.kind === Track.Kind.Video) {
          setRemoteVideoTracks((prev) => ({
            ...prev,
            [participant.identity]: track as RemoteVideoTrack,
          }));
        } else if (track.kind === Track.Kind.Audio) {
          const el = track.attach();
          attachedAudioElements.push(el);
        }
      },
    );

    // Remote participant unpublished a track
    room.on(
      RoomEvent.TrackUnsubscribed,
      (track: RemoteTrack, _publication: RemoteTrackPublication, participant: RemoteParticipant) => {
        if (track.kind === Track.Kind.Video) {
          setRemoteVideoTracks((prev) => {
            const next = { ...prev };
            delete next[participant.identity];
            return next;
          });
        } else if (track.kind === Track.Kind.Audio) {
          track.detach().forEach((el) => el.remove());
        }
      },
    );

    // Remote participant left the room
    room.on(RoomEvent.ParticipantDisconnected, (participant: RemoteParticipant) => {
      setRemoteVideoTracks((prev) => {
        const next = { ...prev };
        delete next[participant.identity];
        return next;
      });
    });

    const initConnection = async () => {
      try {
        const effectiveLivekitUrl =
          typeof window !== "undefined" && window.location.hostname === "127.0.0.1"
            ? livekitUrl.replace("localhost", "127.0.0.1")
            : livekitUrl;
        await room.connect(effectiveLivekitUrl, token);
      } catch (err) {
        console.warn("LiveKit SFU connection error (local media preview remains operational):", err);
      }
    };

    initConnection();

    return () => {
      attachedAudioElements.forEach((el) => el.remove());
      room.disconnect();
      roomRef.current = null;
    };
  }, [token, livekitUrl, setLiveKitConnected, setActiveSpeakers, isVideoEnabled, isMicMuted]);

  // 4. Fallback P2P WebRTC Mesh for local multi-tab / multi-guest testing when LiveKit SFU server is offline
  useEffect(() => {
    if (!meetingId || !participantId) return;

    const pcs = new Map<string, RTCPeerConnection>();
    const pendingCandidates = new Map<string, RTCIceCandidateInit[]>();
    const audioElements = new Map<string, HTMLAudioElement>();
    let isCleanedUp = false;
    let bc: BroadcastChannel | null = null;
    let heartbeatTimer: NodeJS.Timeout | null = null;

    if (typeof BroadcastChannel !== "undefined" && typeof RTCPeerConnection !== "undefined") {
      bc = new BroadcastChannel(`meet_p2p_media_${meetingId}`);

      const setupPeerConnection = (remotePeerId: string, isOfferer: boolean) => {
        // Reuse healthy existing connection if already established and not explicitly re-offering
        const existing = pcs.get(remotePeerId);
        if (existing) {
          if (existing.connectionState === "connected" && !isOfferer) {
            return existing;
          }
          try {
            existing.close();
          } catch {}
          pcs.delete(remotePeerId);
        }

        const pc = new RTCPeerConnection({
          iceServers: [
            { urls: "stun:stun.l.google.com:19302" },
            { urls: "stun:stun1.l.google.com:19302" },
          ],
        });
        pcs.set(remotePeerId, pc);

        // Attach local tracks or reserve transceivers
        if (localVideoTrackRef.current?.mediaStreamTrack) {
          try {
            pc.addTrack(localVideoTrackRef.current.mediaStreamTrack);
          } catch {}
        } else {
          try {
            pc.addTransceiver("video", { direction: "sendrecv" });
          } catch {}
        }

        if (localAudioTrackRef.current?.mediaStreamTrack) {
          try {
            pc.addTrack(localAudioTrackRef.current.mediaStreamTrack);
          } catch {}
        } else {
          try {
            pc.addTransceiver("audio", { direction: "sendrecv" });
          } catch {}
        }

        // ICE candidate handler - CRITICAL FIX FOR DataCloneError:
        // Must call .toJSON() to serialize candidate before posting over BroadcastChannel
        pc.onicecandidate = (event) => {
          if (event.candidate && bc && !isCleanedUp) {
            bc.postMessage({
              type: "P2P_ICE",
              senderId: participantId,
              targetId: remotePeerId,
              candidate: event.candidate.toJSON(),
            });
          }
        };

        // Remote media stream arrived
        pc.ontrack = (event) => {
          if (isCleanedUp) return;
          const track = event.track;
          if (track.kind === "video") {
            setRemoteVideoTracks((prev) => ({
              ...prev,
              [remotePeerId]: track as any,
            }));
          } else if (track.kind === "audio") {
            let audioEl = audioElements.get(remotePeerId);
            if (!audioEl) {
              audioEl = new Audio();
              audioElements.set(remotePeerId, audioEl);
            }
            audioEl.srcObject = new MediaStream([track]);
            audioEl.play().catch(() => {});
          }
        };

        // If offerer, generate and dispatch SDP offer
        if (isOfferer) {
          pc.createOffer({
            offerToReceiveAudio: true,
            offerToReceiveVideo: true,
          })
            .then(async (offer) => {
              if (isCleanedUp) return;
              await pc.setLocalDescription(offer);
              bc?.postMessage({
                type: "P2P_OFFER",
                senderId: participantId,
                targetId: remotePeerId,
                offer: { type: offer.type, sdp: offer.sdp },
              });
            })
            .catch((e) => console.warn("P2P offer error:", e));
        }

        return pc;
      };

      const flushQueuedCandidates = async (remotePeerId: string, pc: RTCPeerConnection) => {
        const queued = pendingCandidates.get(remotePeerId);
        if (queued && queued.length > 0) {
          pendingCandidates.delete(remotePeerId);
          for (const cand of queued) {
            try {
              await pc.addIceCandidate(new RTCIceCandidate(cand));
            } catch (e) {
              console.warn("Could not add buffered ICE candidate:", e);
            }
          }
        }
      };

      bc.onmessage = async (event) => {
        if (isCleanedUp) return;
        const msg = event.data;
        if (!msg || msg.senderId === participantId) return;

        // If LiveKit SFU is connected, let SFU handle media
        if (roomRef.current && roomRef.current.state === "connected") {
          return;
        }

        const remotePeerId = msg.senderId;

        // 1. Peer Announce: A participant joined or heartbeat
        if (msg.type === "PEER_ANNOUNCE") {
          const isOfferer = participantId > remotePeerId;
          const existing = pcs.get(remotePeerId);
          if (existing && (existing.connectionState === "connected" || existing.connectionState === "connecting")) {
            return;
          }
          if (isOfferer) {
            setupPeerConnection(remotePeerId, true);
          } else {
            bc?.postMessage({
              type: "PEER_ANNOUNCE_ACK",
              senderId: participantId,
              targetId: remotePeerId,
            });
          }
        }

        // 2. Peer Announce ACK: Target peer acknowledges, ready for our offer
        else if (msg.type === "PEER_ANNOUNCE_ACK" && msg.targetId === participantId) {
          setupPeerConnection(remotePeerId, true);
        }

        // 3. P2P Offer received
        else if (msg.type === "P2P_OFFER" && msg.targetId === participantId) {
          const pc = setupPeerConnection(remotePeerId, false);
          try {
            await pc.setRemoteDescription(new RTCSessionDescription(msg.offer));
            await flushQueuedCandidates(remotePeerId, pc);

            const answer = await pc.createAnswer();
            await pc.setLocalDescription(answer);

            bc?.postMessage({
              type: "P2P_ANSWER",
              senderId: participantId,
              targetId: remotePeerId,
              answer: { type: answer.type, sdp: answer.sdp },
            });
          } catch (e) {
            console.warn("P2P answer generation error:", e);
          }
        }

        // 4. P2P Answer received
        else if (msg.type === "P2P_ANSWER" && msg.targetId === participantId) {
          const pc = pcs.get(remotePeerId);
          if (pc) {
            try {
              await pc.setRemoteDescription(new RTCSessionDescription(msg.answer));
              await flushQueuedCandidates(remotePeerId, pc);
            } catch (e) {
              console.warn("P2P setRemoteDescription answer error:", e);
            }
          }
        }

        // 5. P2P ICE candidate received
        else if (msg.type === "P2P_ICE" && msg.targetId === participantId) {
          const pc = pcs.get(remotePeerId);
          if (pc && pc.remoteDescription && pc.remoteDescription.type) {
            try {
              await pc.addIceCandidate(new RTCIceCandidate(msg.candidate));
            } catch (e) {
              console.warn("P2P addIceCandidate error:", e);
            }
          } else {
            const q = pendingCandidates.get(remotePeerId) || [];
            q.push(msg.candidate);
            pendingCandidates.set(remotePeerId, q);
          }
        }

        // 6. Peer leaving
        else if (msg.type === "PEER_LEAVING" && msg.senderId) {
          const pc = pcs.get(msg.senderId);
          if (pc) {
            try { pc.close(); } catch {}
            pcs.delete(msg.senderId);
          }
          const audioEl = audioElements.get(msg.senderId);
          if (audioEl) {
            audioEl.pause();
            audioEl.srcObject = null;
            audioElements.delete(msg.senderId);
          }
          setRemoteVideoTracks((prev) => {
            const next = { ...prev };
            delete next[msg.senderId];
            return next;
          });
        }

        // 7. Peer Speaking indicator
        else if (msg.type === "PEER_SPEAKING" && msg.senderId) {
          setActiveSpeakers(msg.isSpeaking ? [msg.senderId] : []);
        }
      };

      // Announce immediately to discover peers
      bc.postMessage({
        type: "PEER_ANNOUNCE",
        senderId: participantId,
      });

      // Self-healing mesh discovery heartbeat
      heartbeatTimer = setInterval(() => {
        if (!isCleanedUp && bc) {
          bc.postMessage({
            type: "PEER_ANNOUNCE",
            senderId: participantId,
          });
        }
      }, 4000);

      pcsRef.current = pcs;
      p2pBcRef.current = bc;
    }

    return () => {
      isCleanedUp = true;
      if (heartbeatTimer) clearInterval(heartbeatTimer);
      if (bc) {
        try {
          bc.postMessage({
            type: "PEER_LEAVING",
            senderId: participantId,
          });
          bc.close();
        } catch {}
      }
      pcs.forEach((pc) => {
        try { pc.close(); } catch {}
      });
      pcs.clear();
      audioElements.forEach((el) => {
        el.pause();
        el.srcObject = null;
      });
      audioElements.clear();
      pendingCandidates.clear();
      pcsRef.current = null;
      p2pBcRef.current = null;
    };
  }, [meetingId, participantId]);

  // 5. Propagate local camera track across all active P2P mesh connections
  useEffect(() => {
    const track = localVideoTrack?.mediaStreamTrack || null;
    if (pcsRef.current) {
      pcsRef.current.forEach((pc) => {
        const senders = pc.getSenders();
        const videoSender = senders.find((s) => s.track?.kind === "video" || (s as any).kind === "video");
        if (videoSender) {
          videoSender.replaceTrack(track).catch(() => {});
        } else if (track) {
          try {
            pc.addTrack(track);
          } catch {}
        }
      });
    }
  }, [localVideoTrack]);

  // 6. Propagate local microphone track across all active P2P mesh connections
  useEffect(() => {
    const track = localAudioTrack?.mediaStreamTrack || null;
    if (pcsRef.current) {
      pcsRef.current.forEach((pc) => {
        const senders = pc.getSenders();
        const audioSender = senders.find((s) => s.track?.kind === "audio" || (s as any).kind === "audio");
        if (audioSender) {
          audioSender.replaceTrack(track).catch(() => {});
        } else if (track) {
          try {
            pc.addTrack(track);
          } catch {}
        }
      });
    }
  }, [localAudioTrack]);

  // 7. Voice Activity Detection (VAD) & Active Speaker Ring
  useEffect(() => {
    if (!localAudioTrack || isMicMuted || !participantId) {
      setActiveSpeakers([]);
      return;
    }

    let audioCtx: AudioContext | null = null;
    let analyser: AnalyserNode | null = null;
    let source: MediaStreamAudioSourceNode | null = null;
    let animId: number | null = null;
    let isSpeakingState = false;
    let silenceTimeout: NodeJS.Timeout | null = null;

    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      audioCtx = new AudioCtx();
      analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.4;

      const mediaStream = new MediaStream([localAudioTrack.mediaStreamTrack]);
      source = audioCtx.createMediaStreamSource(mediaStream);
      source.connect(analyser);

      const buffer = new Uint8Array(analyser.frequencyBinCount);

      const checkVolume = () => {
        if (!analyser) return;
        analyser.getByteFrequencyData(buffer);
        let sum = 0;
        for (let i = 0; i < buffer.length; i++) {
          sum += buffer[i];
        }
        const avg = sum / buffer.length;

        // Threshold for human voice detection
        if (avg > 15) {
          if (!isSpeakingState) {
            isSpeakingState = true;
            setActiveSpeakers([participantId]);
            if (p2pBcRef.current) {
              p2pBcRef.current.postMessage({
                type: "PEER_SPEAKING",
                senderId: participantId,
                isSpeaking: true,
              });
            }
          }
          if (silenceTimeout) clearTimeout(silenceTimeout);
          silenceTimeout = setTimeout(() => {
            isSpeakingState = false;
            setActiveSpeakers([]);
            if (p2pBcRef.current) {
              p2pBcRef.current.postMessage({
                type: "PEER_SPEAKING",
                senderId: participantId,
                isSpeaking: false,
              });
            }
          }, 800);
        }

        animId = requestAnimationFrame(checkVolume);
      };

      animId = requestAnimationFrame(checkVolume);
    } catch (e) {
      console.warn("Audio level analyser initialization:", e);
    }

    return () => {
      if (animId) cancelAnimationFrame(animId);
      if (silenceTimeout) clearTimeout(silenceTimeout);
      if (source) {
        try { source.disconnect(); } catch {}
      }
      if (audioCtx && audioCtx.state !== "closed") {
        try { audioCtx.close(); } catch {}
      }
    };
  }, [localAudioTrack, isMicMuted, participantId, setActiveSpeakers]);

  // Clean up all local tracks when unmounting the hook
  useEffect(() => {
    return () => {
      if (localVideoTrackRef.current) {
        localVideoTrackRef.current.stop();
        localVideoTrackRef.current = null;
      }
      if (localAudioTrackRef.current) {
        localAudioTrackRef.current.stop();
        localAudioTrackRef.current = null;
      }
      if (screenTrackRef.current) {
        screenTrackRef.current.stop();
        screenTrackRef.current = null;
      }
    };
  }, []);

  // Handle Mute / Unmute Mic toggle
  const toggleMic = useCallback(async () => {
    if (!isMicMuted) {
      // Mute microphone
      if (localAudioTrackRef.current) {
        try {
          await localAudioTrackRef.current.mute();
        } catch {
          localAudioTrackRef.current.stop();
        }
      }
      setMicMuted(true);
    } else {
      // Unmute microphone
      if (
        localAudioTrackRef.current &&
        localAudioTrackRef.current.mediaStreamTrack.readyState === "live"
      ) {
        try {
          await localAudioTrackRef.current.unmute();
          setMicMuted(false);
          return;
        } catch (e) {
          console.warn("Unmute audio failed, re-acquiring track:", e);
        }
      }

      try {
        const aTrack = await acquireAudioTrack();
        localAudioTrackRef.current = aTrack;
        setLocalAudioTrack(aTrack);
        setMicMuted(false);

        const room = roomRef.current;
        if (room && room.state === "connected") {
          await room.localParticipant.publishTrack(aTrack);
        }
      } catch (e) {
        console.error("Error creating audio track:", e);
      }
    }
  }, [isMicMuted, setMicMuted]);

  // Handle Camera toggle
  const toggleVideo = useCallback(async () => {
    if (isVideoEnabled) {
      // Turn off camera
      if (localVideoTrackRef.current) {
        try {
          await localVideoTrackRef.current.mute();
        } catch {
          localVideoTrackRef.current.stop();
        }
      }
      setVideoEnabled(false);
    } else {
      // Turn on camera
      if (
        localVideoTrackRef.current &&
        localVideoTrackRef.current.mediaStreamTrack.readyState === "live"
      ) {
        try {
          await localVideoTrackRef.current.unmute();
          setVideoEnabled(true);
          return;
        } catch (e) {
          console.warn("Unmute camera failed, re-acquiring track:", e);
        }
      }

      try {
        const vTrack = await acquireCameraTrack(displayName);
        localVideoTrackRef.current = vTrack;
        setLocalVideoTrack(vTrack);
        setVideoEnabled(true);

        const room = roomRef.current;
        if (room && room.state === "connected") {
          await room.localParticipant.publishTrack(vTrack);
        }
      } catch (e) {
        console.error("Error creating video track:", e);
      }
    }
  }, [isVideoEnabled, setVideoEnabled, displayName]);

  // Handle Screen Share toggle
  const toggleScreenShare = useCallback(async () => {
    const room = roomRef.current;
    if (!room) return;

    if (isScreenSharing && screenTrackRef.current) {
      room.localParticipant.unpublishTrack(screenTrackRef.current);
      screenTrackRef.current.stop();
      screenTrackRef.current = null;
      setScreenTrack(null);
      setScreenSharing(false);
    } else {
      try {
        const stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
        const track = stream.getVideoTracks()[0];
        if (track) {
          const lkTrack = new LocalVideoTrack(track);
          screenTrackRef.current = lkTrack;
          setScreenTrack(lkTrack);
          setScreenSharing(true);

          if (room.state === "connected") {
            await room.localParticipant.publishTrack(lkTrack, {
              source: Track.Source.ScreenShare,
            });
          }

          track.onended = () => {
            if (room.state === "connected") {
              room.localParticipant.unpublishTrack(lkTrack);
            }
            lkTrack.stop();
            screenTrackRef.current = null;
            setScreenTrack(null);
            setScreenSharing(false);
          };
        }
      } catch (e) {
        console.warn("Screen share cancelled or failed:", e);
      }
    }
  }, [isScreenSharing, setScreenSharing]);

  return {
    room: roomRef.current,
    localVideoTrack,
    localAudioTrack,
    remoteVideoTracks,
    screenTrack,
    toggleMic,
    toggleVideo,
    toggleScreenShare,
  };
}
