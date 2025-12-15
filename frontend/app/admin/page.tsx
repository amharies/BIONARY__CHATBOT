"use client";

import { useState, useEffect, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";

export default function AdminPage() {
  const router = useRouter();

  /* Auth Guard */
  useEffect(() => {
    const verify = async () => {
      const token = localStorage.getItem("token");
      console.log("Token from localStorage:", token);
      if (!token) {
        router.replace("/login");
        return;
      }

      try {
        await axios.get(`${process.env.NEXT_PUBLIC_API_URL}/api/verify-token`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
      } catch (error) {
        console.error("Token verification failed:", error);
        localStorage.removeItem("token"); // Clean up invalid token
        router.replace("/login");
      }
    };

    verify();
  }, [router]);

  const logout = () => {
    localStorage.removeItem("token");
    router.replace("/login");
  };

  /* Form State */
  const [formData, setFormData] = useState({
    name_of_event: "",
    event_domain: "",
    date_of_event: "",
    description_insights: "",
    time_of_event: "",
    faculty_coordinators: "",
    student_coordinators: "",
    venue: "",
    mode_of_event: "Offline",
    registration_fee: "0",
    speakers: "",
    perks: "",
    collaboration: "",
  });

  const [status, setStatus] = useState<{ type: "success" | "error" | ""; msg: string }>({
    type: "",
    msg: "",
  });

  const [loading, setLoading] = useState(false);

  const handleChange = (e: any) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  /* Submit */
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setStatus({ type: "", msg: "" });

    const token = localStorage.getItem("token");

    try {
      await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/add-event`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        }
      );

      setStatus({
        type: "success",
        msg: `Success! "${formData.name_of_event}" added.`,
      });
    } catch (error: any) {
      const errMsg = error.response?.data?.detail || "Submission failed";
      setStatus({ type: "error", msg: errMsg });
    } finally {
      setLoading(false);
    }
  };

  /* UI (Dark Theme Version) */
  return (
    <div
      className="min-h-screen p-8"
      style={{ background: "var(--background)", color: "var(--foreground)" }}
    >
      <div
        className="
          max-w-5xl mx-auto rounded-xl p-8
          bg-[rgba(20,20,35,0.85)]
          border border-[rgba(0,255,170,0.25)]
          shadow-[0_0_25px_rgba(0,255,170,0.1)]
          backdrop-blur-xl
        "
      >
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <h1
            className="text-3xl font-bold"
            style={{
              color: "var(--violet)",
              textShadow: "0 0 10px rgba(123,31,162,0.5)",
            }}
          >
            Add New Event
          </h1>

          <div className="flex gap-4">
            <a
              href="/"
              className="hover:opacity-100 opacity-70 text-sm underline"
              style={{ color: "var(--green)" }}
            >
              Back to Chat
            </a>

            <button
              onClick={logout}
              className="text-red-400 hover:text-red-300 text-sm underline"
            >
              Logout
            </button>
          </div>
        </div>

        {/* STATUS MESSAGE */}
        {status.msg && (
          <div
            className={`p-4 mb-6 rounded text-sm ${
              status.type === "success"
                ? "bg-[rgba(0,255,170,0.15)] text-green-300 border border-green-500/40"
                : "bg-[rgba(60,0,0,0.4)] text-red-400 border border-red-600/30"
            }`}
          >
            {status.msg}
          </div>
        )}

        {/* FORM */}
        <form
          onSubmit={handleSubmit}
          className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4"
        >
          {/* Section Headers */}
          <div className="col-span-2 pb-2 mb-2 text-lg font-semibold border-b border-[rgba(255,255,255,0.2)]">
            Core Details
          </div>

          {/* Inputs */}
          <div>
            <label className="label">Event Name <span className="text-red-500">*</span></label>
            <input name="name_of_event" required placeholder="Event Name" onChange={handleChange} className="input" />
          </div>
          <div>
            <label className="label">Domain (AI/ML) <span className="text-red-500">*</span></label>
            <input name="event_domain" required placeholder="Domain (AI/ML)" onChange={handleChange} className="input" />
          </div>
          <div>
            <label className="label">Date <span className="text-red-500">*</span></label>
            <input name="date_of_event" type="date" required onChange={handleChange} className="input" />
          </div>
          <div>
            <label className="label">Time</label>
            <input name="time_of_event" placeholder="Time" onChange={handleChange} className="input" />
          </div>

          <div className="col-span-2 pb-2 mt-4 text-lg font-semibold border-b border-[rgba(255,255,255,0.2)]">
            Logistics
          </div>

          <div>
            <label className="label">Venue</label>
            <input name="venue" placeholder="Venue" onChange={handleChange} className="input" />
          </div>
          <div>
            <label className="label">Mode</label>
            <select name="mode_of_event" onChange={handleChange} className="input">
              <option>Offline</option>
              <option>Online</option>
              <option>Hybrid</option>
            </select>
          </div>
          <div>
            <label className="label">Registration Fee</label>
            <input name="registration_fee" type="number" defaultValue="0" onChange={handleChange} className="input" />
          </div>
          <div>
            <label className="label">Collaboration</label>
            <input name="collaboration" placeholder="Collaboration" onChange={handleChange} className="input" />
          </div>

          <div className="col-span-2 pb-2 mt-4 text-lg font-semibold border-b border-[rgba(255,255,255,0.2)]">
            People
          </div>

          <div>
            <label className="label">Faculty Coordinators</label>
            <input name="faculty_coordinators" placeholder="Faculty Coordinators" onChange={handleChange} className="input" />
          </div>
          <div>
            <label className="label">Student Coordinators</label>
            <input name="student_coordinators" placeholder="Student Coordinators" onChange={handleChange} className="input" />
          </div>
          <div className="col-span-2">
            <label className="label">Speakers</label>
            <input name="speakers" placeholder="Speakers" className="input" onChange={handleChange} />
          </div>

          <div className="col-span-2 pb-2 mt-4 text-lg font-semibold border-b border-[rgba(255,255,255,0.2)]">
            Content (For AI)
          </div>

          <div className="col-span-2">
            <label className="label">Description & Insights <span className="text-red-500">*</span></label>
            <textarea name="description_insights" required placeholder="A detailed summary for the AI to understand the event" onChange={handleChange} className="input h-32" />
          </div>
          <div className="col-span-2">
            <label className="label">Perks</label>
            <textarea name="perks" placeholder="What will attendees gain?" onChange={handleChange} className="input h-20" />
          </div>

          {/* SUBMIT BUTTON */}
          <button
            type="submit"
            disabled={loading}
            className="
              col-span-2 mt-4 py-4 rounded-lg font-bold text-black
              bg-gradient-to-r from-teal-400 to-green-300
              hover:opacity-85 transition shadow-[0_0_15px_rgba(0,255,170,0.4)]
              disabled:opacity-50
            "
          >
            {loading ? "Saving..." : "Submit Event"}
          </button>
        </form>
      </div>
    </div>
  );
}
