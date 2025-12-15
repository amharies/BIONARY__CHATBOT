"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import axios from "axios";

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
            <h3 className="text-sm font-bold mb-2 tracking-wide opacity-70">
              AGENT RESPONSE
            </h3>

            <div className="whitespace-pre-wrap text-white">
              {answer}
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
