"use client";

import { useState } from "react";
import { X, Copy, Check, Share2, Link as LinkIcon, Users, Smartphone, Globe } from "lucide-react";
import { useMeetingStore } from "../stores/useMeetingStore";

interface ShareMeetingModalProps {
  isOpen: boolean;
  onClose: () => void;
  meetingId: string;
}

export function ShareMeetingModal({ isOpen, onClose, meetingId }: ShareMeetingModalProps) {
  const { title } = useMeetingStore();
  const [copiedLink, setCopiedLink] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);

  if (!isOpen) return null;

  const origin = typeof window !== "undefined" ? window.location.origin : "http://localhost:3000";
  const meetingUrl = `${origin}/meeting/${meetingId}`;

  const shareText = `Join my Multilingual AI Meeting: "${title || "AI Meeting Session"}"\n\nDirect Link: ${meetingUrl}\nMeeting Code: ${meetingId}\n\nZero-latency speech translation & real-time multilingual captions.`;

  const whatsappUrl = `https://api.whatsapp.com/send?text=${encodeURIComponent(shareText)}`;

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(meetingUrl);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    } catch {
      // Fallback if clipboard API is blocked
      const el = document.createElement("textarea");
      el.value = meetingUrl;
      document.body.appendChild(el);
      el.select();
      document.execCommand("copy");
      document.body.removeChild(el);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    }
  };

  const handleCopyCode = async () => {
    try {
      await navigator.clipboard.writeText(meetingId);
      setCopiedCode(true);
      setTimeout(() => setCopiedCode(false), 2000);
    } catch {
      setCopiedCode(true);
      setTimeout(() => setCopiedCode(false), 2000);
    }
  };

  const handleNativeShare = async () => {
    if (typeof navigator !== "undefined" && navigator.share) {
      try {
        await navigator.share({
          title: title || "Multilingual AI Meeting",
          text: shareText,
          url: meetingUrl,
        });
      } catch {
        // User cancelled or share aborted
      }
    } else {
      window.open(whatsappUrl, "_blank");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in">
      <div className="w-full max-w-md rounded-2xl border border-surface-200 bg-surface-900 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="h-14 px-5 border-b border-surface-200 flex items-center justify-between">
          <div className="flex items-center space-x-2 text-sm font-semibold text-zinc-100">
            <Share2 className="w-4 h-4 text-emerald-400" />
            <span>Invite & Share Call</span>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-surface-100 text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4 overflow-y-auto flex-1 text-xs">
          {/* Primary Action: Share on WhatsApp */}
          <div className="space-y-2">
            <label className="text-zinc-300 font-semibold block">Share to WhatsApp</label>
            <a
              href={whatsappUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full py-3 px-4 rounded-xl bg-[#25D366] hover:bg-[#20ba5a] text-white font-semibold flex items-center justify-center space-x-2.5 shadow-lg shadow-emerald-500/20 transition-all cursor-pointer"
            >
              {/* WhatsApp SVG Icon */}
              <svg className="w-5 h-5 fill-current" viewBox="0 0 24 24">
                <path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z" />
              </svg>
              <span>Send Link on WhatsApp</span>
            </a>
          </div>

          {/* Copy Direct Meeting Link */}
          <div className="space-y-1.5">
            <label className="text-zinc-300 font-semibold flex items-center justify-between">
              <span className="flex items-center space-x-1.5">
                <LinkIcon className="w-3.5 h-3.5 text-brand-primary" />
                <span>Direct Call Link</span>
              </span>
              <span className="text-[10px] text-zinc-500 font-normal">Click to copy</span>
            </label>
            <div className="flex space-x-2">
              <input
                type="text"
                readOnly
                value={meetingUrl}
                className="flex-1 bg-surface-100 border border-surface-200 rounded-xl px-3 py-2 text-zinc-200 select-all focus:outline-none focus:border-brand-primary font-mono text-[11px]"
              />
              <button
                onClick={handleCopyLink}
                className={`px-3 py-2 rounded-xl border flex items-center space-x-1 font-semibold transition-all ${
                  copiedLink
                    ? "bg-emerald-600/30 border-emerald-500 text-emerald-300"
                    : "bg-surface-100 border-surface-200 text-zinc-100 hover:bg-surface-200"
                }`}
              >
                {copiedLink ? (
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <Copy className="w-3.5 h-3.5" />
                )}
                <span>{copiedLink ? "Copied!" : "Copy"}</span>
              </button>
            </div>
          </div>

          {/* Meeting Room ID / Code */}
          <div className="space-y-1.5">
            <label className="text-zinc-300 font-semibold flex items-center space-x-1.5">
              <Globe className="w-3.5 h-3.5 text-emerald-400" />
              <span>Room ID / Code</span>
            </label>
            <div className="flex space-x-2">
              <input
                type="text"
                readOnly
                value={meetingId}
                className="flex-1 bg-surface-100 border border-surface-200 rounded-xl px-3 py-2 text-zinc-200 font-mono text-[11px] select-all focus:outline-none focus:border-brand-primary"
              />
              <button
                onClick={handleCopyCode}
                className={`px-3 py-2 rounded-xl border flex items-center space-x-1 font-semibold transition-all ${
                  copiedCode
                    ? "bg-emerald-600/30 border-emerald-500 text-emerald-300"
                    : "bg-surface-100 border-surface-200 text-zinc-100 hover:bg-surface-200"
                }`}
              >
                {copiedCode ? (
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <Copy className="w-3.5 h-3.5" />
                )}
                <span>{copiedCode ? "Copied!" : "Copy Code"}</span>
              </button>
            </div>
          </div>

          {/* Native Share / Mobile option */}
          <div className="pt-1">
            <button
              onClick={handleNativeShare}
              className="w-full py-2.5 px-3 rounded-xl bg-surface-100 hover:bg-surface-200 border border-surface-200 text-zinc-200 font-medium flex items-center justify-center space-x-2 transition-colors"
            >
              <Smartphone className="w-3.5 h-3.5 text-brand-primary" />
              <span>Share via Other Apps...</span>
            </button>
          </div>

          {/* Instructions card */}
          <div className="p-3 rounded-xl bg-surface-800/80 border border-surface-200 text-zinc-400 space-y-1">
            <div className="font-semibold text-zinc-300 flex items-center space-x-1.5">
              <Users className="w-3.5 h-3.5 text-brand-primary" />
              <span>Connecting Another Person:</span>
            </div>
            <p className="text-[11px] leading-relaxed">
              When the invited person opens the WhatsApp link on their phone or computer, they will
              immediately join this live meeting room with real-time audio translation and live
              camera video.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-surface-200 bg-surface-800/40 flex items-center justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-surface-100 hover:bg-surface-200 border border-surface-200 text-zinc-200 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
