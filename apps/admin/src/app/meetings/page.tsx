"use client";

import { useState } from "react";
import {
  CalendarCheck,
  Search,
  FileText,
  Download,
  X,
  Languages,
  ShieldCheck,
  Clock,
  Users,
} from "lucide-react";
import { MeetingStatus } from "@multilingual/contracts";

interface MeetingHistoryItem {
  meetingId: string;
  title: string;
  status: MeetingStatus;
  date: string;
  duration: string;
  participantsCount: number;
  segmentsCount: number;
  languages: string;
}

interface MockTranscriptSegment {
  source_segment_id: string;
  speaker_id: string;
  speaker_name: string;
  source_language: string;
  target_language: string;
  original_text: string;
  translated_text: string;
  start_ms: number;
  end_ms: number;
}

const MEETINGS_DATA: MeetingHistoryItem[] = [
  {
    meetingId: "meet_001",
    title: "Global Architecture Summit: H2 Roadmap",
    status: MeetingStatus.ACTIVE,
    date: "2026-09-21 10:00 UTC",
    duration: "42m 15s",
    participantsCount: 8,
    segmentsCount: 142,
    languages: "eng → spa, jpn, deu",
  },
  {
    meetingId: "meet_002",
    title: "Executive Product Review & AI Model Evaluation",
    status: MeetingStatus.ACTIVE,
    date: "2026-09-21 11:30 UTC",
    duration: "18m 30s",
    participantsCount: 5,
    segmentsCount: 68,
    languages: "eng → fra, zho",
  },
  {
    meetingId: "meet_003",
    title: "Sprint Retrospective & Sprint 14 Planning",
    status: MeetingStatus.ENDED,
    date: "2026-09-20 15:00 UTC",
    duration: "55m 00s",
    participantsCount: 12,
    segmentsCount: 284,
    languages: "eng → spa",
  },
  {
    meetingId: "meet_004",
    title: "Cross-Functional Security & Compliance Audit",
    status: MeetingStatus.ENDED,
    date: "2026-09-19 14:00 UTC",
    duration: "1h 10m",
    participantsCount: 6,
    segmentsCount: 310,
    languages: "eng → jpn, fra",
  },
];

const SAMPLE_SEGMENTS: Record<string, MockTranscriptSegment[]> = {
  meet_001: [
    {
      source_segment_id: "src_seg_1001_001",
      speaker_id: "usr_001",
      speaker_name: "Devon Vance",
      source_language: "eng",
      target_language: "spa",
      original_text: "Welcome team, today we are finalizing the H2 architecture roadmap.",
      translated_text:
        "Bienvenidos equipo, hoy estamos finalizando la hoja de ruta de la arquitectura del segundo semestre.",
      start_ms: 0,
      end_ms: 3200,
    },
    {
      source_segment_id: "src_seg_1001_002",
      speaker_id: "usr_002",
      speaker_name: "Kenji Sato",
      source_language: "jpn",
      target_language: "eng",
      original_text: "東京チームの準備は完了しています。超低遅延パイプラインの検証を進めています。",
      translated_text:
        "The Tokyo team is fully prepared. We are proceeding with ultra-low latency pipeline validation.",
      start_ms: 3400,
      end_ms: 6800,
    },
    {
      source_segment_id: "src_seg_1001_003",
      speaker_id: "usr_003",
      speaker_name: "Elena Rostova",
      source_language: "eng",
      target_language: "deu",
      original_text: "The translation latency benchmarks for Tier 1 remain below 500 milliseconds.",
      translated_text:
        "Die Übersetzungslatenz-Benchmarks für Tier 1 bleiben unter 500 Millisekunden.",
      start_ms: 7100,
      end_ms: 10400,
    },
  ],
};

export default function MeetingsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedMeeting, setSelectedMeeting] = useState<MeetingHistoryItem | null>(null);

  const filteredMeetings = MEETINGS_DATA.filter(
    (m) =>
      m.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.languages.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  const activeSegments: MockTranscriptSegment[] = selectedMeeting
    ? (SAMPLE_SEGMENTS[selectedMeeting.meetingId] ?? SAMPLE_SEGMENTS.meet_001 ?? [])
    : [];

  const handleExportJson = () => {
    if (!selectedMeeting) return;
    const dataStr =
      "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(activeSegments, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute(
      "download",
      `compliance_transcript_${selectedMeeting.meetingId}.json`,
    );
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto select-none">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <CalendarCheck className="w-5 h-5 text-brand-primary" />
            <h1 className="text-xl font-bold text-zinc-100">Meeting Compliance & Transcripts</h1>
          </div>
          <p className="text-xs text-zinc-400 mt-1">
            Audit meeting history, inspect lineaged transcript segments, and export compliance
            records.
          </p>
        </div>
      </div>

      {/* Search Bar */}
      <div className="flex items-center justify-between gap-4 bg-surface-800/40 p-3 rounded-xl border border-surface-200">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search meetings by title or language code..."
            className="w-full bg-surface-100 border border-surface-200 rounded-lg pl-9 pr-3 py-1.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-brand-primary"
          />
        </div>
        <div className="text-xs text-zinc-400 font-mono">
          Showing {filteredMeetings.length} of {MEETINGS_DATA.length} meetings
        </div>
      </div>

      {/* Meetings Table */}
      <div className="rounded-2xl border border-surface-200 bg-surface-800/40 overflow-hidden">
        <table className="w-full text-left text-xs">
          <thead className="bg-surface-800/80 border-b border-surface-200 text-zinc-400 uppercase tracking-wider font-semibold text-[10px]">
            <tr>
              <th className="px-5 py-3">Meeting</th>
              <th className="px-5 py-3">Status</th>
              <th className="px-5 py-3">Date / Start Time</th>
              <th className="px-5 py-3">Duration</th>
              <th className="px-5 py-3">Participants</th>
              <th className="px-5 py-3">Transcripts</th>
              <th className="px-5 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-200/50 text-zinc-300">
            {filteredMeetings.map((m) => (
              <tr key={m.meetingId} className="hover:bg-surface-800/60 transition-colors">
                <td className="px-5 py-3.5">
                  <div className="font-semibold text-zinc-100">{m.title}</div>
                  <div className="text-[10px] text-zinc-500 font-mono">ID: {m.meetingId}</div>
                </td>

                <td className="px-5 py-3.5">
                  {m.status === MeetingStatus.ACTIVE ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      Active
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-surface-100 text-zinc-400 border border-surface-200">
                      Ended
                    </span>
                  )}
                </td>

                <td className="px-5 py-3.5 text-zinc-400 font-mono text-[11px]">{m.date}</td>
                <td className="px-5 py-3.5 font-mono text-zinc-300">{m.duration}</td>
                <td className="px-5 py-3.5 font-mono text-zinc-300">
                  <div className="flex items-center gap-1.5">
                    <Users className="w-3.5 h-3.5 text-zinc-500" />
                    <span>{m.participantsCount}</span>
                  </div>
                </td>
                <td className="px-5 py-3.5 font-mono text-zinc-300">
                  <span className="px-2 py-0.5 rounded bg-surface-100 text-blue-300 text-[10px] border border-surface-200">
                    {m.segmentsCount} segments
                  </span>
                </td>
                <td className="px-5 py-3.5 text-right">
                  <button
                    onClick={() => setSelectedMeeting(m)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-100 hover:bg-surface-200 text-zinc-200 text-xs font-medium transition-colors"
                  >
                    <FileText className="w-3.5 h-3.5 text-brand-primary" />
                    <span>Inspect</span>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Compliance Transcript Drawer / Modal */}
      {selectedMeeting && (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/70 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-2xl h-full bg-surface-900 border-l border-surface-200 p-6 flex flex-col shadow-2xl">
            {/* Drawer Header */}
            <div className="flex items-start justify-between pb-4 border-b border-surface-200">
              <div>
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <span className="text-xs font-bold text-emerald-400 tracking-wider uppercase">
                    Lineaged Transcript Audit (Invariant #2)
                  </span>
                </div>
                <h2 className="text-base font-bold text-zinc-100 mt-1">{selectedMeeting.title}</h2>
                <div className="flex items-center gap-4 text-[11px] text-zinc-400 mt-1 font-mono">
                  <span>Duration: {selectedMeeting.duration}</span>
                  <span>•</span>
                  <span>{selectedMeeting.segmentsCount} total records</span>
                </div>
              </div>

              <button
                onClick={() => setSelectedMeeting(null)}
                className="p-1.5 rounded-lg hover:bg-surface-100 text-zinc-400 hover:text-zinc-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Export Toolbar */}
            <div className="py-3 flex items-center justify-between border-b border-surface-200/60">
              <div className="text-xs text-zinc-400 flex items-center gap-1.5">
                <Languages className="w-3.5 h-3.5 text-brand-primary" />
                <span>Channels: {selectedMeeting.languages}</span>
              </div>

              <button
                onClick={handleExportJson}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-primary hover:bg-blue-600 text-xs font-semibold text-white transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export Lineaged JSON</span>
              </button>
            </div>

            {/* Transcript Segments List */}
            <div className="flex-1 overflow-y-auto py-4 space-y-3.5">
              {activeSegments.map((seg) => (
                <div
                  key={seg.source_segment_id}
                  className="rounded-xl border border-surface-200 bg-surface-800/60 p-4 space-y-2 text-xs"
                >
                  <div className="flex items-center justify-between text-[11px]">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-zinc-200">{seg.speaker_name}</span>
                      <span className="px-1.5 py-0.2 rounded bg-surface-100 text-zinc-400 font-mono text-[10px]">
                        {seg.source_language.toUpperCase()} → {seg.target_language.toUpperCase()}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 font-mono text-zinc-500 text-[10px]">
                      <Clock className="w-3 h-3" />
                      <span>
                        {(seg.start_ms / 1000).toFixed(1)}s - {(seg.end_ms / 1000).toFixed(1)}s
                      </span>
                    </div>
                  </div>

                  {/* Lineage ID Badge */}
                  <div className="font-mono text-[10px] text-zinc-500">
                    Lineage ID:{" "}
                    <code className="text-brand-primary font-semibold">
                      #{seg.source_segment_id}
                    </code>
                  </div>

                  {/* Original Text */}
                  <div className="text-zinc-300">
                    <span className="text-[10px] font-semibold text-zinc-500 uppercase mr-1">
                      Original:
                    </span>
                    <span>{seg.original_text}</span>
                  </div>

                  {/* Translated Text */}
                  <div className="text-emerald-300 bg-emerald-500/5 p-2 rounded-lg border border-emerald-500/10">
                    <span className="text-[10px] font-semibold text-emerald-500 uppercase mr-1">
                      AI Translated:
                    </span>
                    <span>{seg.translated_text}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
