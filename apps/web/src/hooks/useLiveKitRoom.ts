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
} from "livekit-client";
import { useMeetingStore } from "../stores/useMeetingStore";

export function useLiveKitRoom(
  livekitUrl: string = process.env.NEXT_PUBLIC_LIVEKIT_URL || "ws://localhost:7880",
  token: string | null,
) {
  const roomRef = useRef<Room | null>(null);
  const [localVideoTrack, setLocalVideoTrack] = useState<LocalVideoTrack | null>(null);
  const [localAudioTrack, setLocalAudioTrack] = useState<LocalAudioTrack | null>(null);
  const [screenTrack, setScreenTrack] = useState<LocalVideoTrack | null>(null);

  const {
    setLiveKitConnected,
    setActiveSpeakers,
    isMicMuted,
    isVideoEnabled,
    isScreenSharing,
    setMicMuted,
    setVideoEnabled,
    setScreenSharing,
  } = useMeetingStore();

  // Initialize Room and Media Connection
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

    // Room event listeners
    room.on(RoomEvent.Connected, () => {
      setLiveKitConnected(true);
    });

    room.on(RoomEvent.Disconnected, () => {
      setLiveKitConnected(false);
    });

    room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
      setActiveSpeakers(speakers.map((s) => s.identity));
    });

    const initConnection = async () => {
      try {
        await room.connect(livekitUrl, token);

        // Publish local camera and mic
        if (isVideoEnabled) {
          try {
            const vTrack = await createLocalVideoTrack();
            await room.localParticipant.publishTrack(vTrack);
            setLocalVideoTrack(vTrack);
          } catch (e) {
            console.warn("Could not publish camera track:", e);
            setVideoEnabled(false);
          }
        }

        if (!isMicMuted) {
          try {
            const aTrack = await createLocalAudioTrack();
            await room.localParticipant.publishTrack(aTrack);
            setLocalAudioTrack(aTrack);
          } catch (e) {
            console.warn("Could not publish microphone track:", e);
            setMicMuted(true);
          }
        }
      } catch (err) {
        console.error("Failed to connect to LiveKit SFU:", err);
      }
    };

    initConnection();

    return () => {
      room.disconnect();
      roomRef.current = null;
    };
  }, [token, livekitUrl, setLiveKitConnected, setActiveSpeakers, setMicMuted, setVideoEnabled]);

  // Handle Mute / Unmute Mic toggle
  const toggleMic = useCallback(async () => {
    const room = roomRef.current;
    if (!room) return;

    if (localAudioTrack) {
      if (isMicMuted) {
        await localAudioTrack.unmute();
        setMicMuted(false);
      } else {
        await localAudioTrack.mute();
        setMicMuted(true);
      }
    } else if (isMicMuted) {
      try {
        const aTrack = await createLocalAudioTrack();
        await room.localParticipant.publishTrack(aTrack);
        setLocalAudioTrack(aTrack);
        setMicMuted(false);
      } catch (e) {
        console.error("Error creating audio track:", e);
      }
    }
  }, [localAudioTrack, isMicMuted, setMicMuted]);

  // Handle Camera toggle
  const toggleVideo = useCallback(async () => {
    const room = roomRef.current;
    if (!room) return;

    if (localVideoTrack) {
      if (isVideoEnabled) {
        await localVideoTrack.mute();
        setVideoEnabled(false);
      } else {
        await localVideoTrack.unmute();
        setVideoEnabled(true);
      }
    } else if (!isVideoEnabled) {
      try {
        const vTrack = await createLocalVideoTrack();
        await room.localParticipant.publishTrack(vTrack);
        setLocalVideoTrack(vTrack);
        setVideoEnabled(true);
      } catch (e) {
        console.error("Error creating video track:", e);
      }
    }
  }, [localVideoTrack, isVideoEnabled, setVideoEnabled]);

  // Handle Screen Share toggle
  const toggleScreenShare = useCallback(async () => {
    const room = roomRef.current;
    if (!room) return;

    if (isScreenSharing && screenTrack) {
      room.localParticipant.unpublishTrack(screenTrack);
      screenTrack.stop();
      setScreenTrack(null);
      setScreenSharing(false);
    } else {
      try {
        const stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
        const track = stream.getVideoTracks()[0];
        if (track) {
          const lkTrack = new LocalVideoTrack(track);
          await room.localParticipant.publishTrack(lkTrack, {
            source: Track.Source.ScreenShare,
          });
          setScreenTrack(lkTrack);
          setScreenSharing(true);

          track.onended = () => {
            room.localParticipant.unpublishTrack(lkTrack);
            setScreenTrack(null);
            setScreenSharing(false);
          };
        }
      } catch (e) {
        console.warn("Screen share cancelled or failed:", e);
      }
    }
  }, [isScreenSharing, screenTrack, setScreenSharing]);

  return {
    room: roomRef.current,
    localVideoTrack,
    localAudioTrack,
    screenTrack,
    toggleMic,
    toggleVideo,
    toggleScreenShare,
  };
}
