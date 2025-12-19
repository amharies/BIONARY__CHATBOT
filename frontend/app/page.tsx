"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import axios from "axios";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function ChatPage() {
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSearch = async (e: FormEvent) => {
    e.preventDefault();
    if (!query) return;

    setLoading(true);
    setAnswer("");

    try {
      const res = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/chat`,
        { query }
      );
      setAnswer(res.data.answer);
    } catch (error) {
      console.error(error);
      setAnswer("Error connecting to the agent.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex flex-col items-center p-8"
      style={{ background: "var(--background)", color: "var(--foreground)" }}
    >
      {/* TITLE */}
      <h1 className="text-4xl font-bold mb-2"
        style={{ color: "var(--violet)", textShadow: "0 0 10px rgba(123,31,162,0.6)" }}>
        Bionary Search Agent
      </h1>

      {/* SUBTITLE */}
      <p className="mb-8 opacity-70">Ask anything about past club events</p>

      <div className="w-full max-w-2xl">

        {/* SEARCH BAR */}
        <form onSubmit={handleSearch} className="flex gap-3 mb-6">
          <input
            type="text"
            placeholder="e.g., What events covered AI?"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="
              flex-1 px-4 py-3 rounded-lg border
              bg-[rgba(20,20,30,0.7)]
              text-white
              placeholder-[rgba(0,255,170,0.5)]
              border-teal-400
              focus:outline-none
              focus:ring-2
              focus:ring-teal-500
            "
          />

          <button
            type="submit"
            disabled={loading}
            className="
              px-6 py-3 rounded-lg font-medium
              text-black
              bg-gradient-to-r from-teal-400 to-green-300
              hover:opacity-85
              disabled:opacity-50
              transition
            "
          >
            {loading ? "Thinking..." : "Ask"}
          </button>
        </form>

        {/* ANSWER CARD */}
        {answer && (
          <div
            className="
              p-6 rounded-xl 
              border border-[rgba(0,255,170,0.25)]
              bg-[rgba(20,20,35,0.85)]
              shadow-[0_0_20px_rgba(0,255,170,0.05)]
            "
          >
            <h3 className="text-sm font-bold mb-4 tracking-wide opacity-70 border-b border-gray-700 pb-2">
              AGENT RESPONSE
            </h3>

            <div className="text-white text-sm leading-relaxed">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  table: ({ node, ...props }) => (
                    <div className="overflow-hidden my-6 rounded-lg border-2 border-teal-500/30 shadow-lg shadow-teal-500/10">
                      <table className="min-w-full text-left border-collapse" {...props} />
                    </div>
                  ),
                  thead: ({ node, ...props }) => (
                    <thead className="bg-[#1a1a2e] text-teal-300 uppercase tracking-wider text-xs" {...props} />
                  ),
                  th: ({ node, ...props }) => (
                    <th className="p-4 border-b-2 border-teal-500/30 font-bold" {...props} />
                  ),
                  td: ({ node, ...props }) => (
                    <td className="p-4 border-b border-gray-700/50 align-top hover:bg-white/5 transition-colors" {...props} />
                  ),
                  strong: ({ node, ...props }) => (
                    <strong className="text-teal-400 font-bold" {...props} />
                  ),
                  ul: ({ node, ...props }) => (
                    <ul className="list-disc pl-5 my-2 space-y-1 text-gray-300" {...props} />
                  ),
                  p: ({ node, ...props }) => (
                    <p className="mb-3 last:mb-0" {...props} />
                  ),
                }}
              >
                {answer}
              </ReactMarkdown>
            </div>
          </div>
        )}
      </div>

      {/* ADMIN LINK */}
      <div className="mt-12">
        <Link
          href="/admin"
          className="text-sm underline opacity-70 hover:opacity-100 transition"
        >
          Go to Admin Dashboard
        </Link>
      </div>
    </div>
  );
}
