"use client";

import { useState } from "react";

export default function Home() {
  const [input, setInput] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [logs, setLogs] = useState<string[]>([]);
  const [screenshot, setScreenshot] = useState("");

  const runAI = async () => {
    setLoading(true);
    setResult(null);
    setStatus("Running AI...");
    setLogs([]);

    try {
      const res = await fetch("http://localhost:3001/run_full_workflow", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text: input }),
      });

      setStatus("Searching memory...");
      const data = await res.json();
      setResult(data);
      setStatus("Completed");
      setLogs(data.logs || []);
    } catch (err) {
      console.error(err);
      setStatus("Error occurred");
      alert("Error calling AI backend");
    }

    setLoading(false);
  };

  const handleApprove = async () => {
    setStatus("Executing automation...");

    const res = await fetch("http://localhost:3001/run_browser_automation", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        clinical: result.clinical,
        coding: result.coding,
      }),
    });

    await res.json();

    const imgRes = await fetch("http://localhost:3001/get_screenshot", {
      method: "POST",
    });
    const imgData = await imgRes.json();
    setScreenshot(`data:image/png;base64,${imgData.image}`);

    setStatus("Automation completed ✅");

    setLogs((prev) => [
      ...prev,
      "Browser automation executed",
      "Form submitted successfully",
    ]);
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

      {status && (
        <p className="mt-4 text-blue-600 font-medium">{status}</p>
      )}

      {/* Results */}
      {result && (
        <>
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
                onClick={handleApprove}
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
          </div>

          {logs.length > 0 && (
            <div className="w-full max-w-2xl bg-gray-900 text-white p-4 mt-6 rounded-lg">
              <h3 className="text-lg font-semibold mb-2">System Logs</h3>
              <ul className="text-sm space-y-1">
                {logs.map((log, i) => (
                  <li key={i}>• {log}</li>
                ))}
              </ul>
            </div>
          )}

          {screenshot && (
            <div className="mt-6">
              <h3 className="font-semibold mb-2">Automation Proof</h3>
              <img
                src={screenshot}
                alt="Automation Screenshot"
                className="rounded-lg shadow"
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}