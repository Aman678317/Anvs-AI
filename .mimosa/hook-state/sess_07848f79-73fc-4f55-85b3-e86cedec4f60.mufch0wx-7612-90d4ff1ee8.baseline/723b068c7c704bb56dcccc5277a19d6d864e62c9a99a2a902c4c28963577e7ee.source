"use client";

import { useState } from "react";
import { X, Sparkles, Send, CheckSquare, Bookmark, Loader2 } from "lucide-react";
import { useMeetingStore } from "../stores/useMeetingStore";

interface AssistantPanelProps {
  onAskQuery: (question: string) => void;
  onClose: () => void;
}

const QUICK_PROMPTS = [
  "Summarize key discussion points so far",
  "What action items have been assigned?",
  "What decisions were finalized?",
  "List any unresolved budget questions",
];

export function AssistantPanel({ onAskQuery, onClose }: AssistantPanelProps) {
  const { assistantQueries, meetingActionItems, addAssistantQuery } = useMeetingStore();
  const [question, setQuestion] = useState("");

  const handleAsk = (queryText: string) => {
    if (!queryText.trim()) return;

    // Optimistically create loading query item
    const queryId = `client_q_${Date.now()}`;
    addAssistantQuery({
      query_id: queryId,
      question: queryText.trim(),
      is_loading: true,
      timestamp_ms: Date.now(),
    });

    onAskQuery(queryText.trim());
    setQuestion("");
  };

  return (
    <aside className="w-80 md:w-96 h-full border-l border-surface-200/60 bg-surface-900/95 backdrop-blur-md flex flex-col z-30">
      {/* Header */}
      <div className="h-14 px-4 border-b border-surface-200 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-4 h-4 text-purple-400" />
          <h2 className="text-sm font-semibold text-zinc-100">AI Meeting Copilot</h2>
          <span className="text-[10px] bg-purple-500/20 text-purple-300 font-mono px-1.5 py-0.5 rounded border border-purple-500/30">
            RAG
          </span>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg hover:bg-surface-100 text-zinc-400 hover:text-zinc-200"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Extracted Meeting Action Items Section */}
        {meetingActionItems.length > 0 && (
          <div className="rounded-xl bg-surface-100/60 border border-surface-200 p-3 space-y-2">
            <div className="flex items-center space-x-1.5 text-xs font-semibold text-emerald-400">
              <CheckSquare className="w-3.5 h-3.5" />
              <span>Extracted Action Items</span>
            </div>
            <ul className="space-y-1.5">
              {meetingActionItems.map((item, idx) => (
                <li key={idx} className="flex items-start space-x-2 text-xs text-zinc-300">
                  <span className="mt-1 w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
                  <span className="leading-snug">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Quick Suggestion Chips */}
        {assistantQueries.length === 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-zinc-400">Suggested questions:</p>
            <div className="flex flex-col space-y-1.5">
              {QUICK_PROMPTS.map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => handleAsk(prompt)}
                  className="text-left p-2 rounded-lg bg-surface-100/70 hover:bg-surface-200/70 border border-surface-200 text-xs text-zinc-300 hover:text-white transition-colors flex items-center justify-between"
                >
                  <span className="truncate">{prompt}</span>
                  <Sparkles className="w-3 h-3 text-purple-400 shrink-0 ml-1" />
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Query History */}
        {assistantQueries.map((q) => (
          <div
            key={q.query_id}
            className="rounded-xl border border-surface-200 bg-surface-800/80 p-3.5 space-y-2 text-xs shadow-sm"
          >
            {/* User Question */}
            <div className="font-semibold text-zinc-200 flex items-start space-x-1.5">
              <span className="text-brand-primary">Q:</span>
              <span>{q.question}</span>
            </div>

            {/* AI Answer */}
            {q.is_loading ? (
              <div className="flex items-center space-x-2 text-purple-300 py-1 font-medium">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Searching meeting transcripts...</span>
              </div>
            ) : (
              <div className="text-zinc-300 leading-relaxed space-y-2 pt-1 border-t border-surface-200/50">
                <p>{q.answer || "No response found."}</p>

                {/* Citations Lineage Badges (Invariant #2) */}
                {q.citations && q.citations.length > 0 && (
                  <div className="flex flex-wrap gap-1 items-center pt-1">
                    <Bookmark className="w-3 h-3 text-zinc-500 mr-1" />
                    <span className="text-[10px] text-zinc-500">Citations:</span>
                    {q.citations.map((cite, i) => (
                      <span
                        key={i}
                        className="px-1.5 py-0.5 rounded bg-surface-100 text-brand-primary font-mono text-[10px] border border-surface-200"
                        title={`Segment ID: ${cite}`}
                      >
                        #{cite.slice(0, 10)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Input Box */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleAsk(question);
        }}
        className="p-3 border-t border-surface-200 flex space-x-2 bg-surface-900"
      >
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask AI Copilot about meeting..."
          className="flex-1 bg-surface-100 border border-surface-200 rounded-xl px-3 py-2 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-brand-accent"
        />
        <button
          type="submit"
          disabled={!question.trim()}
          className="p-2.5 rounded-xl bg-brand-accent hover:bg-purple-600 disabled:opacity-40 text-white font-medium transition-colors"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </aside>
  );
}
