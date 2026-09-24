"use client";

import { useState, useRef, useEffect } from "react";
import { X, Send } from "lucide-react";
import { useMeetingStore } from "../stores/useMeetingStore";

interface ChatPanelProps {
  onSendMessage: (text: string) => void;
  onClose: () => void;
}

export function ChatPanel({ onSendMessage, onClose }: ChatPanelProps) {
  const { chatMessages } = useMeetingStore();
  const [inputText, setInputText] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    onSendMessage(inputText.trim());
    setInputText("");
  };

  return (
    <aside className="w-80 md:w-96 h-full border-l border-surface-200/60 bg-surface-900/95 backdrop-blur-md flex flex-col z-30 transition-transform">
      {/* Header */}
      <div className="h-14 px-4 border-b border-surface-200 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-zinc-100">Meeting Chat</h2>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg hover:bg-surface-100 text-zinc-400 hover:text-zinc-200"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Messages List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {chatMessages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-center text-xs text-zinc-500">
            No messages yet. Send a message to participants in this room.
          </div>
        ) : (
          chatMessages.map((msg) => (
            <div
              key={msg.id}
              className={`flex flex-col ${msg.is_self ? "items-end" : "items-start"}`}
            >
              <span className="text-[11px] font-medium text-zinc-400 mb-1 px-1">
                {msg.sender_name}
              </span>
              <div
                className={`max-w-[85%] rounded-2xl px-3 py-2 text-xs leading-relaxed ${
                  msg.is_self
                    ? "bg-brand-primary text-white rounded-tr-none"
                    : "bg-surface-100 border border-surface-200 text-zinc-200 rounded-tl-none"
                }`}
              >
                {msg.text}
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Box */}
      <form onSubmit={handleSubmit} className="p-3 border-t border-surface-200 flex space-x-2">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Send a message..."
          className="flex-1 bg-surface-100 border border-surface-200 rounded-xl px-3 py-2 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-brand-primary"
        />
        <button
          type="submit"
          disabled={!inputText.trim()}
          className="p-2.5 rounded-xl bg-brand-primary hover:bg-blue-600 disabled:opacity-40 text-white font-medium transition-colors"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </aside>
  );
}
