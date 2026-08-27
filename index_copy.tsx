import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

const TITLE = "SRM TIMETABLE AND WORKLOAD";
const DESCRIPTION =
  "Upload syllabus and faculty data, configure teaching hours, and generate university faculty workload allocations.";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: TITLE },
      { name: "description", content: DESCRIPTION },
      { property: "og:title", content: TITLE },
      { property: "og:description", content: DESCRIPTION },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Index,
});

type Faculty = {
  id: string;
  name: string;
  dept: string;
  facultyId: string;
  theory: number;
  lab: number;
  incharge: number;
  limit: number;
};

const INITIAL: Faculty[] = [
  {
    id: "1",
    name: "Dr. Sarah Jenkins",
    dept: "Computer Science",
    facultyId: "CS-102",
    theory: 2,
    lab: 3,
    incharge: 2,
    limit: 18,
  },
  {
    id: "2",
    name: "Prof. Marcus Vane",
    dept: "Mathematics",
    facultyId: "MA-405",
    theory: 2,
    lab: 0,
    incharge: 0,
    limit: 14,
  },
  {
    id: "3",
    name: "Elena Rodriguez",
    dept: "Applied Physics",
    facultyId: "PH-210",
    theory: 4,
    lab: 3,
    incharge: 0,
    limit: 20,
  },
];

const UPLOADS = [
  { key: "syllabus", label: "Syllabus Excel" },
  { key: "faculty", label: "Faculty List" },
  { key: "rooms", label: "Class/Lab List" },
  { key: "hours", label: "Hours Reference" },
] as const;

const selectClass =
  "text-xs border border-slate-200 rounded px-2 py-1 bg-white outline-none focus:ring-1 focus:ring-brand-accent";

const parseCleanNumber = (val: any) => {
  if (val == null) return 0;
  const str = String(val);
  if (str.trim().toLowerCase() === "none" || str.trim() === "") return 0;
  const match = str.match(/-?\d+/);
  return match ? parseInt(match[0], 10) : 0;
};

const mapFaculty = (d: any) => ({
  id: d.faculty_id || d.id,
  name: d.name,
  dept: d.department || d.dept,
  facultyId: d.faculty_id || d.facultyId,
  theory: d.theory_hours ?? d.theory ?? 0,
  lab: d.lab_hours ?? d.lab ?? 0,
  incharge: d.incharge_hours ?? d.incharge ?? 0,
  limit: d.max_hours_limit ?? d.limit ?? 0,
  total: d.total_calculated ?? d.total ?? undefined,
});

function Index() {
  const [level, setLevel] = useState<"ug" | "pg">("ug");
  const [scope, setScope] = useState("whole");
  const [files, setFiles] = useState<Record<string, string>>({});
  const [rows, setRows] = useState<Faculty[]>([]);
  const [approved, setApproved] = useState(false);
  const [results, setResults] = useState<Faculty[] | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const fetchFacultyList = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/admin/faculty-list");
      if (!res.ok) throw new Error("Network response was not ok");
      const data = await res.json();
      setFetchError(null);
      if (Array.isArray(data)) {
        setRows(data.map(mapFaculty));
      } else if (data && Array.isArray(data.faculty)) {
        setRows(data.faculty.map(mapFaculty));
      }
    } catch (err) {
      console.error("Failed to fetch faculty:", err);
      setFetchError("Could not connect to the backend server. Please ensure the FastAPI server is running.");
      setRows([]); // Ensure we don't quietly fallback to mock array
    }
  };

  useEffect(() => {
    fetchFacultyList();
  }, []);

  const handleFileUpload = async (key: string, file: File) => {
    setFiles((prev) => ({ ...prev, [key]: file.name }));
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("file_type", key);

      const res = await fetch("http://localhost:8000/api/admin/upload-metadata", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error("Upload failed");

      // Refresh faculty list after successful upload
      await fetchFacultyList();
    } catch (err) {
      console.error("Upload error:", err);
      alert(`Failed to upload ${key}. Please try again.`);
    } finally {
      setIsUploading(false);
    }
  };

  const update = (facultyId: string, patch: Partial<Faculty>) => {
    setRows((prev) => prev.map((r) => ((r.facultyId || r.id) === facultyId ? { ...r, ...patch } : r)));
    setResults(null);
  };

  const exportPDF = () => {
    if (!results) return;
    const doc = new jsPDF();
    
    doc.setFontSize(18);
    doc.setTextColor(30, 58, 138); // blue-900
    doc.text("SRM Timetable and Workload Report", 14, 22);
    
    doc.setFontSize(11);
    doc.setTextColor(100);
    doc.text(`Generated on: ${new Date().toLocaleDateString()} at ${new Date().toLocaleTimeString()}`, 14, 30);
    
    const tableColumn = ["Faculty ID", "Name", "Department", "Theory", "Lab", "Incharge", "Total Hours", "Status"];
    const tableRows = results.map(r => {
      const t = (r as any).total ?? (parseCleanNumber(r.theory) * 4 + parseCleanNumber(r.lab) * 2 + parseCleanNumber(r.incharge));
      const limit = parseCleanNumber(r.limit) || 1;
      const status = t > limit ? `OVERLOADED (+${(t - limit).toFixed(1)})` : "OK";
      return [
        r.facultyId,
        r.name,
        r.dept,
        parseCleanNumber(r.theory).toString(),
        parseCleanNumber(r.lab).toString(),
        parseCleanNumber(r.incharge).toString(),
        t.toFixed(1),
        status
      ];
    });

    autoTable(doc, {
      head: [tableColumn],
      body: tableRows,
      startY: 35,
      theme: 'grid',
      styles: { fontSize: 9, cellPadding: 3 },
      headStyles: { fillColor: [30, 58, 138], textColor: 255, fontStyle: 'bold' },
      alternateRowStyles: { fillColor: [248, 250, 252] },
      columnStyles: { 7: { fontStyle: 'bold' } },
      didParseCell: function(data) {
        if (data.section === 'body' && data.column.index === 7) {
          if (data.cell.raw !== 'OK') {
            data.cell.styles.textColor = [220, 38, 38]; // Red
          } else {
            data.cell.styles.textColor = [22, 163, 74]; // Green
          }
        }
      }
    });
    
    doc.save("srm_workload_report.pdf");
  };

  const total = (r: Faculty) => parseCleanNumber(r.theory) * 4 + parseCleanNumber(r.lab) * 2 + parseCleanNumber(r.incharge);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50 p-8 font-body text-slate-900">
      <div className="mx-auto max-w-6xl space-y-8">
        <header className="grid grid-cols-[minmax(0,1fr)_auto] items-end gap-4 border-b border-slate-200 pb-6">
          <div className="min-w-0">
            <h1 className="font-heading text-3xl font-bold tracking-tight text-blue-900">
              SRM TIMETABLE AND WORKLOAD
            </h1>
            <p className="mt-1 text-slate-500">University Scheduling &amp; Workload Management</p>
          </div>
          <div className="flex shrink-0 items-center gap-3 rounded-lg border border-slate-200 bg-white p-2 shadow-sm">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-blue-100 text-blue-700 font-bold uppercase text-lg">
              A
            </div>
            <div className="pr-4">
              <p className="text-sm font-bold leading-none text-slate-800">admin</p>
              <p className="mt-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                System Administrator
              </p>
            </div>
          </div>
        </header>

        {/* Step 01 */}
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-6 py-4">
            <h2 className="flex items-center gap-2 font-heading font-semibold text-brand-primary">
              <span className="flex size-6 items-center justify-center rounded-full bg-brand-primary text-[10px] font-bold text-primary-foreground">
                01
              </span>
              Resource Configuration
            </h2>
          </div>

          <div className="grid grid-cols-1 gap-8 p-6 md:grid-cols-2">
            <div className="space-y-6">
              <div className="flex flex-col gap-2">
                <label className="text-xs font-bold uppercase tracking-widest text-slate-500">
                  Academic Level
                </label>
                <div className="inline-flex w-fit rounded-lg bg-slate-100 p-1">
                  <button
                    onClick={() => setLevel("ug")}
                    className={`rounded-md px-6 py-2 text-sm font-medium transition-colors ${
                      level === "ug"
                        ? "bg-white text-brand-primary shadow-sm"
                        : "text-slate-500 hover:text-slate-700"
                    }`}
                  >
                    Undergraduate
                  </button>
                  <button
                    onClick={() => setLevel("pg")}
                    className={`rounded-md px-6 py-2 text-sm font-medium transition-colors ${
                      level === "pg"
                        ? "bg-white text-brand-primary shadow-sm"
                        : "text-slate-500 hover:text-slate-700"
                    }`}
                  >
                    Postgraduate
                  </button>
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <label
                  htmlFor="scope"
                  className="text-xs font-bold uppercase tracking-widest text-slate-500"
                >
                  Syllabus Scope
                </label>
                <select
                  id="scope"
                  value={scope}
                  onChange={(e) => setScope(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-brand-accent focus:ring-2 focus:ring-brand-accent/20"
                >
                  <option value="whole">Whole Syllabus (All Years)</option>
                  <option value="current">Current Semester Syllabus Only</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {UPLOADS.map((u) => (
                <label
                  key={u.key}
                  className="group flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-slate-200 p-4 transition-colors hover:border-brand-accent/40"
                >
                  <div className="flex size-8 items-center justify-center rounded-lg bg-slate-50 text-slate-400 group-hover:text-brand-accent">
                    +
                  </div>
                  <span className="text-center text-[11px] font-medium text-slate-600">
                    {files[u.key] ?? u.label}
                  </span>
                  <input
                    type="file"
                    accept=".xlsx,.xls,.csv"
                    className="hidden"
                    disabled={isUploading}
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) handleFileUpload(u.key, f);
                      e.target.value = ""; // Reset value to allow uploading the same file again
                    }}
                  />
                </label>
              ))}
            </div>
          </div>
        </section>

        {/* Step 02 */}
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-6 py-4">
            <h2 className="flex items-center gap-2 font-heading font-semibold text-brand-primary">
              <span className="flex size-6 items-center justify-center rounded-full bg-brand-primary text-[10px] font-bold text-primary-foreground">
                02
              </span>
              Faculty Assignment Matrix
            </h2>
            <span className="text-xs italic text-slate-400">
              Showing {rows.length} entries detected from upload
            </span>
          </div>

          {fetchError && (
            <div className="m-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-600">
              {fetchError}
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-slate-50/50">
                  {["Faculty Details", "Theory Hrs", "Lab Hrs", "Incharge", "Limit"].map((h) => (
                    <th
                      key={h}
                      className="px-6 py-4 text-xs font-bold uppercase tracking-widest text-slate-400"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((r) => (
                  <tr key={r.facultyId || r.id} className="transition-colors hover:bg-slate-50/50">
                    <td className="px-6 py-4">
                      <p className="text-sm font-semibold text-blue-900">{r.name}</p>
                      <p className="mt-0.5 font-mono text-xs text-slate-500">
                        {r.facultyId} • {r.dept}
                      </p>
                    </td>
                    <td className="px-6 py-4">
                      <select
                        aria-label={`Theory hours for ${r.name}`}
                        className={selectClass}
                        value={parseCleanNumber(r.theory)}
                        onChange={(e) => update(r.facultyId || r.id, { theory: Number(e.target.value) })}
                      >
                        <option value={1}>1hr session</option>
                        <option value={2}>2hr session</option>
                        <option value={4}>4hr session</option>
                      </select>
                    </td>
                    <td className="px-6 py-4">
                      <select
                        aria-label={`Lab hours for ${r.name}`}
                        className={selectClass}
                        value={parseCleanNumber(r.lab)}
                        onChange={(e) => update(r.facultyId || r.id, { lab: Number(e.target.value) })}
                      >
                        <option value={0}>None</option>
                        <option value={3}>3hr Lab</option>
                        <option value={6}>6hr Lab</option>
                      </select>
                    </td>
                    <td className="px-6 py-4">
                      <select
                        aria-label={`Incharge hours for ${r.name}`}
                        className={selectClass}
                        value={parseCleanNumber(r.incharge)}
                        onChange={(e) => update(r.facultyId || r.id, { incharge: Number(e.target.value) })}
                      >
                        <option value={0}>None</option>
                        <option value={2}>2hr (Active)</option>
                      </select>
                    </td>
                    <td className="px-6 py-4">
                      <input
                        type="number"
                        aria-label={`Total allocated hours limit for ${r.name}`}
                        value={parseCleanNumber(r.limit)}
                        onChange={(e) => update(r.facultyId || r.id, { limit: Number(e.target.value) })}
                        className="w-16 rounded border border-slate-200 px-2 py-1 text-xs outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Step 03 */}
        <section className="space-y-6 pb-8">
          <div className="flex flex-col items-center justify-between gap-8 rounded-2xl bg-gradient-to-r from-blue-900 to-indigo-800 p-8 text-white shadow-xl shadow-blue-900/20 md:flex-row">
            <div className="flex flex-col items-start gap-6 md:flex-row md:items-center">
              <div className="flex items-center gap-3">
                <button
                  role="switch"
                  aria-checked={approved}
                  aria-label="Approve workload data"
                  onClick={() => {
                    setApproved((a) => !a);
                    setResults(null);
                  }}
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ${
                    approved ? "bg-brand-success" : "bg-white/25"
                  }`}
                >
                  <span
                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow transition duration-200 ${
                      approved ? "translate-x-5" : "translate-x-0"
                    }`}
                  />
                </button>
                <span className="text-sm font-medium">Approve Workload Data</span>
              </div>
              <div className="hidden h-8 w-px bg-white/20 md:block" />
              <p className="max-w-xs text-sm text-slate-400">
                Unlocks generation engine and final semester validation.
              </p>
            </div>

            <button
              disabled={!approved || isGenerating}
              onClick={async () => {
                try {
                  setIsGenerating(true);
                  const cleanPayload = rows.map(r => ({
                    faculty_id: r.facultyId || r.id,
                    department: r.dept,
                    theory_hours: parseCleanNumber(r.theory),
                    lab_hours: parseCleanNumber(r.lab),
                    incharge_hours: parseCleanNumber(r.incharge),
                    max_hours_limit: parseCleanNumber(r.limit)
                  }));

                  const res = await fetch("http://localhost:8000/api/admin/generate-workload", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(cleanPayload),
                  });
                  if (!res.ok) throw new Error("Network response was not ok");
                  const data = await res.json();
                  if (Array.isArray(data)) {
                    setResults(data.map(mapFaculty));
                  } else if (data && Array.isArray(data.workload)) {
                    setResults(data.workload.map(mapFaculty));
                  } else {
                    setResults(cleanPayload.map(mapFaculty));
                  }
                } catch (err) {
                  console.error("Failed to generate workload:", err);
                  alert("Failed to generate workload. Please check if backend is reachable.");
                } finally {
                  setIsGenerating(false);
                }
              }}
              className="rounded-xl bg-white text-blue-900 px-10 py-4 font-heading font-bold shadow-xl shadow-black/10 transition-all hover:bg-blue-50 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
            >
              {isGenerating ? "Generating..." : "Generate Workload"}
            </button>
          </div>

          {results && (
            <div className="rounded-2xl border border-blue-100 bg-white p-6 shadow-lg shadow-blue-900/5">
              <div className="mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <h3 className="font-heading text-xl font-bold text-blue-900">
                    Official Workload Allocation
                  </h3>
                  <p className="text-sm text-slate-500 mt-1">Generated and verified allocations for the current semester.</p>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-emerald-700">
                    Ready for Review
                  </span>
                  <button
                    onClick={exportPDF}
                    className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-bold text-white shadow-md shadow-blue-600/20 transition-all hover:bg-blue-700 active:scale-95"
                  >
                    <svg className="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    Export to PDF
                  </button>
                </div>
              </div>

              <div className="overflow-x-auto rounded-xl border border-slate-200">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-3 font-semibold text-slate-700">Faculty ID</th>
                      <th className="px-4 py-3 font-semibold text-slate-700">Name</th>
                      <th className="px-4 py-3 font-semibold text-slate-700">Department</th>
                      <th className="px-4 py-3 font-semibold text-slate-700 text-center">Theory</th>
                      <th className="px-4 py-3 font-semibold text-slate-700 text-center">Lab</th>
                      <th className="px-4 py-3 font-semibold text-slate-700 text-center">Incharge</th>
                      <th className="px-4 py-3 font-semibold text-slate-700 text-center">Total Hrs</th>
                      <th className="px-4 py-3 font-semibold text-slate-700 text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {results.map((r) => {
                      const t = (r as any).total ?? total(r);
                      const cleanedLimit = parseCleanNumber(r.limit) || 1;
                      const isOverloaded = t > cleanedLimit;
                      return (
                        <tr key={r.facultyId || r.id} className="hover:bg-slate-50/50 transition-colors">
                          <td className="px-4 py-3 font-mono text-xs text-slate-500">{r.facultyId}</td>
                          <td className="px-4 py-3 font-medium text-slate-900">{r.name}</td>
                          <td className="px-4 py-3 text-slate-600">{r.dept}</td>
                          <td className="px-4 py-3 text-center">{parseCleanNumber(r.theory)}</td>
                          <td className="px-4 py-3 text-center">{parseCleanNumber(r.lab)}</td>
                          <td className="px-4 py-3 text-center">{parseCleanNumber(r.incharge)}</td>
                          <td className="px-4 py-3 text-center font-bold text-blue-900">{t.toFixed(1)}</td>
                          <td className="px-4 py-3 text-right">
                            {isOverloaded ? (
                              <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-1 text-xs font-semibold text-red-700 ring-1 ring-inset ring-red-600/10">
                                ⚠ OVERLOAD (+{(t - cleanedLimit).toFixed(1)})
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-1 text-xs font-semibold text-green-700 ring-1 ring-inset ring-green-600/20">
                                ✓ OK
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
