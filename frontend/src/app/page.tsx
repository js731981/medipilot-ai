"use client";

import { useState } from "react";

export default function Home() {
  const [input, setInput] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");

  const runAI = async () => {
    setLoading(true);
    setResult(null);

    try {
      const res = await fetch("http://localhost:3001/run_full_workflow", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text: input }),
      });

      const data = await res.json();
      setResult(data);
    } catch (err) {
      console.error(err);
      alert("Error calling AI backend");
    }

    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gray-100 p-6 flex flex-col items-center">
      <h1 className="text-3xl font-bold mb-6">MediPilot AI 🏥</h1>

      {/* Input */}
      <textarea
        className="w-full max-w-2xl p-4 border rounded-lg mb-4"
        rows={4}
        placeholder="Enter clinical text..."
        value={input}
        onChange={(e) => setInput(e.target.value)}
      />

      <button
        onClick={runAI}
        className="bg-blue-600 text-white px-6 py-2 rounded-lg mb-6"
      >
        {loading ? "Running..." : "Run AI"}
      </button>

      {/* Results */}
      {result && (
        <div className="w-full max-w-2xl bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Results</h2>

          <p><strong>Symptoms:</strong> {result.clinical?.symptoms?.join(", ")}</p>
          <p><strong>Diagnosis:</strong> {result.clinical?.diagnosis?.join(", ")}</p>
          <p><strong>Procedures:</strong> {result.clinical?.procedures?.join(", ")}</p>

          <hr className="my-4" />

          <p><strong>ICD Codes:</strong> {result.coding?.icd_codes?.join(", ")}</p>
          <p><strong>CPT Codes:</strong> {result.coding?.cpt_codes?.join(", ")}</p>
          <p><strong>Confidence:</strong> {result.coding?.confidence}</p>

          <hr className="my-4" />

          <div className="flex gap-4">
            <button
              className="bg-green-600 text-white px-4 py-2 rounded"
              onClick={async () => {
                setStatus("Running automation...");

                await fetch("http://localhost:3001/run_browser_automation", {
                  method: "POST",
                  headers: {
                    "Content-Type": "application/json",
                  },
                  body: JSON.stringify({
                    clinical: result.clinical,
                    coding: result.coding,
                  }),
                });

                setStatus("Form submitted successfully!");
              }}
            >
              Approve
            </button>

            <button
              className="bg-red-600 text-white px-4 py-2 rounded"
              onClick={() => alert("Rejected")}
            >
              Reject
            </button>
          </div>

          {status ? (
            <p className="mt-3 text-sm text-gray-700">{status}</p>
          ) : null}
        </div>
      )}
    </div>
  );
}