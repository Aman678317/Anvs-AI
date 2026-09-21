"use client";

import { useState } from "react";
import { X, Globe2, Headphones, Mic, Check } from "lucide-react";
import { SUPPORTED_LANGUAGES, LanguageTier } from "@multilingual/contracts";
import { useMeetingStore } from "../stores/useMeetingStore";

interface LanguageSelectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLanguageChanged: (listeningLang: string) => void;
}

export function LanguageSelectorModal({
  isOpen,
  onClose,
  onLanguageChanged,
}: LanguageSelectorModalProps) {
  const {
    spokenLanguage,
    listeningLanguage,
    setSpokenLanguage,
    setListeningLanguage,
  } = useMeetingStore();

  const [selectedSpoken, setSelectedSpoken] = useState(spokenLanguage);
  const [selectedListening, setSelectedListening] = useState(listeningLanguage);

  if (!isOpen) return null;

  const languagesList = Object.values(SUPPORTED_LANGUAGES);
  const tier1Languages = languagesList.filter((l) => l.tier === LanguageTier.TIER_1);
  const tier2Languages = languagesList.filter((l) => l.tier === LanguageTier.TIER_2);

  const handleSave = () => {
    setSpokenLanguage(selectedSpoken);
    setListeningLanguage(selectedListening);
    onLanguageChanged(selectedListening);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in">
      <div className="w-full max-w-lg rounded-2xl border border-surface-200 bg-surface-900 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="h-14 px-5 border-b border-surface-200 flex items-center justify-between">
          <div className="flex items-center space-x-2 text-sm font-semibold text-zinc-100">
            <Globe2 className="w-4 h-4 text-brand-primary" />
            <span>Personalized Language Preferences</span>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-surface-100 text-zinc-400 hover:text-zinc-200"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 space-y-5 overflow-y-auto flex-1">
          {/* Spoken Language Picker */}
          <div className="space-y-2">
            <label className="flex items-center space-x-1.5 text-xs font-semibold text-zinc-300">
              <Mic className="w-3.5 h-3.5 text-brand-primary" />
              <span>I will speak in (Microphone Input):</span>
            </label>
            <select
              value={selectedSpoken}
              onChange={(e) => setSelectedSpoken(e.target.value)}
              className="w-full rounded-xl bg-surface-100 border border-surface-200 px-3 py-2.5 text-xs text-zinc-100 focus:outline-none focus:border-brand-primary"
            >
              <optgroup label="Tier 1 (Ultra-Low Latency < 500ms)">
                {tier1Languages.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.name_en} ({l.name_native})
                  </option>
                ))}
              </optgroup>
              <optgroup label="Tier 2 (High Accuracy < 1200ms)">
                {tier2Languages.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.name_en} ({l.name_native})
                  </option>
                ))}
              </optgroup>
            </select>
          </div>

          {/* Listening Language Picker */}
          <div className="space-y-2">
            <label className="flex items-center space-x-1.5 text-xs font-semibold text-zinc-300">
              <Headphones className="w-3.5 h-3.5 text-emerald-400" />
              <span>I want to listen & read captions in (Translation Target):</span>
            </label>
            <select
              value={selectedListening}
              onChange={(e) => setSelectedListening(e.target.value)}
              className="w-full rounded-xl bg-surface-100 border border-surface-200 px-3 py-2.5 text-xs text-zinc-100 focus:outline-none focus:border-emerald-500"
            >
              <optgroup label="Tier 1 (Ultra-Low Latency < 500ms)">
                {tier1Languages.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.name_en} ({l.name_native})
                  </option>
                ))}
              </optgroup>
              <optgroup label="Tier 2 (High Accuracy < 1200ms)">
                {tier2Languages.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.name_en} ({l.name_native})
                  </option>
                ))}
              </optgroup>
            </select>
            <p className="text-[11px] text-zinc-500">
              Live captions and AI synthetic audio tracks will be routed strictly in this language.
            </p>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-surface-200 bg-surface-800/40 flex items-center justify-end space-x-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-medium text-zinc-400 hover:text-zinc-200 hover:bg-surface-100 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-brand-primary hover:bg-blue-600 text-white transition-colors shadow-sm"
          >
            <Check className="w-3.5 h-3.5" />
            <span>Apply Preferences</span>
          </button>
        </div>
      </div>
    </div>
  );
}
