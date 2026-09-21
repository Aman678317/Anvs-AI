"use client";

import { useEffect } from "react";
import { Room, RemoteTrackPublication, Track } from "livekit-client";
import { AudioStreamType } from "@multilingual/contracts";
import { useMeetingStore } from "../stores/useMeetingStore";

export function useAudioRouter(room: Room | null) {
  const { audioTrackMode, originalGain, translatedGain, listeningLanguage, availableTracks } =
    useMeetingStore();

  useEffect(() => {
    if (!room) return;

    // Apply volume balancing and track subscription preferences
    room.remoteParticipants.forEach((participant) => {
      participant.trackPublications.forEach((pub: RemoteTrackPublication) => {
        if (pub.kind !== Track.Kind.Audio) return;

        const trackSid = pub.trackSid;
        const matchingMeta = availableTracks.find((t) => t.track_sid === trackSid);

        const isSynthetic =
          matchingMeta?.stream_type === AudioStreamType.TRANSLATED_SYNTHETIC ||
          pub.trackName.includes("translated") ||
          pub.trackName.includes("synthetic");

        const audioElement = pub.audioTrack?.attachedElements[0] as HTMLAudioElement | undefined;

        if (audioTrackMode === "translated") {
          if (isSynthetic) {
            // Check if track matches user's current listening language
            const isTargetLang =
              !matchingMeta?.language ||
              matchingMeta.language.toLowerCase() === listeningLanguage.toLowerCase();

            if (isTargetLang) {
              pub.setEnabled(true);
              if (audioElement) audioElement.volume = Math.min(1.0, Math.max(0.0, translatedGain));
            } else {
              // Mute synthetic tracks for other languages
              pub.setEnabled(false);
            }
          } else {
            // Mute or duck original human audio when listening to translation
            const duckedGain = originalGain > 0 ? originalGain * 0.1 : 0;
            if (duckedGain === 0) {
              pub.setEnabled(false);
            } else {
              pub.setEnabled(true);
              if (audioElement) audioElement.volume = duckedGain;
            }
          }
        } else {
          // 'original' mode: listen directly to human speaker
          if (isSynthetic) {
            pub.setEnabled(false);
          } else {
            pub.setEnabled(true);
            if (audioElement) audioElement.volume = Math.min(1.0, Math.max(0.0, originalGain));
          }
        }
      });
    });
  }, [room, audioTrackMode, originalGain, translatedGain, listeningLanguage, availableTracks]);
}
