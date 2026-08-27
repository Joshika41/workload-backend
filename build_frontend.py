import os

content = """import { createFileRoute, useRouter } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import { useAuth } from "../lib/auth-context";

const TITLE = "SRM TIMETABLE AND WORKLOAD";
const DESCRIPTION = "Admin Dashboard for managing faculty and parallel class timetables.";

export const Route = createFileRoute("/")({
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
  is_overloaded?: boolean;
  warning_message?: string;
};

type TimetableBlock = {
  id?: number;
  faculty_id: string;
  section: string;
  subject: string;
  day: number;
  period: number;
};

const INITIAL: Faculty[] = [
  { id: "1", name: "Dr. Sarah Jenkins", dept: "Computer Science", facultyId: "FAC001", theory: 2, lab: 3, incharge: 2, limit: 18 },
  { id: "2", name: "Prof. Marcus Vane", dept: "Mathematics", facultyId: "FAC002", theory: 2, lab: 0, incharge: 0, limit: 14 },
];

function Index() {
  const { isAuthenticated, user, isLoading, logout } = useAuth();
  const router = useRouter();

  const [activeTab, setActiveTab] = useState<"faculty" | "classes">("faculty");
  const [selectedFaculty, setSelectedFaculty] = useState<Faculty | null>(null);
  const [isBatchGenerating, setIsBatchGenerating] = useState(false);
  const [timetableBlocks, setTimetableBlocks] = useState<TimetableBlock[]>([]);
  const [rows, setRows] = useState<Faculty[]>(INITIAL);
  const [metadata, setMetadata] = useState<{sections: string[]}>({ sections: ["MCA I-A", "MCA I-B", "MCA II-A", "MCA II-B", "MCA GEN AI I-A", "MCA GEN AI I-B", "MCA GEN AI II-A", "MCA GEN AI II-B"] });

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        router.navigate({ to: "/login" });
      } else if (user?.role !== "ADMIN") {
        router.navigate({ to: "/faculty" });
      } else {
        fetchTimetable();
      }
    }
  }, [isLoading, isAuthenticated, user, router]);

  const fetchTimetable = async () => {
    try {
      const token = localStorage.getItem("srm_token") || "";
      const res = await fetch("http://127.0.0.1:8000/api/admin/timetable", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setTimetableBlocks(data.blocks || data || []);
      }
    } catch (err) {
      console.error("Failed to fetch timetable:", err);
    }
  };

  const handleBatchGenerate = async () => {
    setIsBatchGenerating(true);
    try {
      const token = localStorage.getItem("srm_token") || "";
      const res = await fetch("http://127.0.0.1:8000/api/admin/generate-batch", {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        await fetchTimetable();
        alert("Batch generation successful!");
      } else {
        alert("Batch generation failed.");
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsBatchGenerating(false);
    }
  };

  return (
    <div className="flex h-screen w-full bg-slate-50 text-slate-900 font-sans overflow-hidden">
      {/* SIDEBAR */}
      <aside className="w-64 bg-slate-900 text-white flex flex-col shadow-2xl relative z-20">
        <div className="p-6 border-b border-slate-800">
          <h1 className="font-heading font-black text-xl tracking-tight text-white flex flex-col">
            <span>SRM</span>
            <span className="text-blue-400 text-sm">ADMIN DASHBOARD</span>
          </h1>
        </div>
        
        <nav className="flex-1 px-4 py-6 flex flex-col gap-2">
          <button 
            onClick={() => setActiveTab("faculty")}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg font-semibold text-sm transition-all ${activeTab === 'faculty' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>
            Faculty History
          </button>
          
          <button 
            onClick={() => setActiveTab("classes")}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg font-semibold text-sm transition-all ${activeTab === 'classes' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
            Class Timetables
          </button>
        </nav>
        
        <div className="p-4 border-t border-slate-800">
          <button onClick={logout} className="w-full py-2 text-sm text-slate-400 hover:text-red-400 font-medium transition-colors">
            Sign Out
          </button>
        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main className="flex-1 relative h-full flex flex-col overflow-hidden bg-slate-50">
        
        {/* TOP BAR */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 shrink-0">
          <h2 className="text-xl font-heading font-bold text-slate-800">
            {activeTab === 'faculty' ? 'Faculty Workload History' : 'Master Class Timetables'}
          </h2>
          {activeTab === 'classes' && (
            <button 
              onClick={handleBatchGenerate}
              disabled={isBatchGenerating}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-md font-semibold text-sm shadow-sm transition-all disabled:opacity-70"
            >
              {isBatchGenerating ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                  Processing Batch...
                </>
              ) : (
                'Generate All Timetables'
              )}
            </button>
          )}
        </header>

        {/* SCROLLABLE CONTENT */}
        <div className="flex-1 overflow-auto relative">
          
          {/* FACULTY TAB */}
          {activeTab === 'faculty' && (
            <div className="p-8 h-full flex gap-8">
              <div className={`flex-1 transition-all duration-300 ${selectedFaculty ? 'mr-96' : ''}`}>
                <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-slate-50 border-b border-slate-200">
                      <tr>
                        <th className="px-6 py-4 font-semibold text-slate-600">ID</th>
                        <th className="px-6 py-4 font-semibold text-slate-600">Name</th>
                        <th className="px-6 py-4 font-semibold text-slate-600">Department</th>
                        <th className="px-6 py-4 font-semibold text-slate-600 text-center">Total Hrs</th>
                        <th className="px-6 py-4 font-semibold text-slate-600 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {rows.map(r => (
                        <tr 
                          key={r.facultyId} 
                          onClick={() => setSelectedFaculty(r)}
                          className={`cursor-pointer transition-colors ${selectedFaculty?.facultyId === r.facultyId ? 'bg-blue-50/60' : 'hover:bg-slate-50'}`}
                        >
                          <td className="px-6 py-4 font-mono text-xs text-slate-500">{r.facultyId}</td>
                          <td className="px-6 py-4 font-medium text-slate-900">{r.name}</td>
                          <td className="px-6 py-4 text-slate-600">{r.dept}</td>
                          <td className="px-6 py-4 text-center font-bold text-blue-900">{r.theory + r.lab + r.incharge} / {r.limit}</td>
                          <td className="px-6 py-4 text-right">
                            <span className="text-blue-600 font-medium text-xs">View Matrix &rarr;</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* SLIDE OUT PANEL */}
              <div className={`fixed inset-y-0 right-0 w-96 bg-white shadow-2xl border-l border-slate-200 transform transition-transform duration-300 z-30 ${selectedFaculty ? 'translate-x-0' : 'translate-x-full'}`}>
                {selectedFaculty && (
                  <div className="h-full flex flex-col">
                    <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50">
                      <div>
                        <h3 className="font-bold text-lg text-slate-800">{selectedFaculty.name}</h3>
                        <p className="text-xs text-slate-500 font-mono">{selectedFaculty.facultyId} &middot; {selectedFaculty.dept}</p>
                      </div>
                      <button onClick={() => setSelectedFaculty(null)} className="p-2 text-slate-400 hover:text-slate-600 bg-white rounded-full shadow-sm">
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                      </button>
                    </div>
                    
                    <div className="p-6 flex-1 overflow-y-auto">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4">Personal Timetable</h4>
                      <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                        <table className="w-full text-xs text-center border-collapse">
                          <thead className="bg-slate-50">
                            <tr>
                              <th className="border-b border-r border-slate-200 p-2 text-slate-500 font-medium">Day</th>
                              <th className="border-b border-slate-200 p-2 text-slate-500 font-medium">Periods</th>
                            </tr>
                          </thead>
                          <tbody>
                            {["Mon", "Tue", "Wed", "Thu", "Fri"].map((dayName, dIdx) => (
                              <tr key={dIdx} className="border-b border-slate-100 last:border-0">
                                <td className="p-3 border-r border-slate-100 font-medium text-slate-600 bg-slate-50/50">{dayName}</td>
                                <td className="p-2">
                                  <div className="flex flex-wrap gap-1.5 justify-center">
                                    {timetableBlocks.filter(b => b.day === dIdx && b.faculty_id === selectedFaculty.facultyId).map((b, i) => (
                                      <div key={i} className="px-2 py-1 bg-indigo-50 border border-indigo-100 rounded text-indigo-700 font-semibold shadow-sm">
                                        P{b.period+1}: {b.subject} ({b.section})
                                      </div>
                                    ))}
                                    {timetableBlocks.filter(b => b.day === dIdx && b.faculty_id === selectedFaculty.facultyId).length === 0 && (
                                      <span className="text-slate-300">-</span>
                                    )}
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* CLASSES TAB */}
          {activeTab === 'classes' && (
            <div className="p-8">
              {isBatchGenerating && (
                <div className="absolute inset-0 bg-white/80 backdrop-blur-sm z-10 flex flex-col items-center justify-center">
                  <div className="w-16 h-16 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
                  <h3 className="mt-6 text-xl font-bold text-blue-900 font-heading">Generating Master Matrices</h3>
                  <p className="text-sm text-slate-500 mt-2 max-w-md text-center">The CP-SAT engine is actively scanning all hard mathematical constraints for 8 sections parallelly.</p>
                </div>
              )}
              
              <div className="grid grid-cols-1 gap-10">
                {metadata.sections.map(section => (
                  <div key={section} className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                    <div className="bg-slate-50 border-b border-slate-200 px-6 py-4">
                      <h3 className="font-heading font-bold text-lg text-slate-800">{section} Timetable</h3>
                    </div>
                    <div className="p-6 overflow-x-auto">
                      <table className="w-full text-left border-collapse border border-slate-200 rounded-lg">
                        <thead className="bg-blue-900 text-white">
                          <tr>
                            <th className="px-4 py-3 font-semibold text-sm border-r border-blue-800 w-32">Day</th>
                            {[0,1,2,3,4,5,6,7].map(p => (
                              <th key={p} className="px-4 py-3 font-semibold text-sm text-center border-r border-blue-800 min-w-[120px]">
                                Period {p + 1}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-200">
                          {["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"].map((dayName, dIndex) => (
                            <tr key={dayName} className="hover:bg-slate-50 transition-colors">
                              <td className="px-4 py-3 font-bold text-slate-700 bg-slate-50 border-r border-slate-200 whitespace-nowrap">
                                {dayName}
                              </td>
                              {[0,1,2,3,4,5,6,7].map(pIndex => {
                                const blocks = timetableBlocks.filter(b => b.day === dIndex && b.period === pIndex && b.section === section);
                                return (
                                  <td key={pIndex} className="px-4 py-2 border-r border-slate-200 align-top min-h-[60px] bg-white">
                                    {blocks.length > 0 ? (
                                      <div className="flex flex-col gap-1.5">
                                        {blocks.map((b, i) => (
                                          <div key={i} className="flex flex-col rounded-md px-2 py-1.5 bg-blue-50 ring-1 ring-inset ring-blue-600/20 shadow-sm">
                                            <span className="text-[11px] font-bold text-blue-800 leading-tight">{b.subject}</span>
                                            <span className="text-[10px] font-medium text-blue-600 leading-tight mt-0.5">{b.faculty_id}</span>
                                          </div>
                                        ))}
                                      </div>
                                    ) : (
                                      <div className="flex h-full items-center justify-center text-slate-300">-</div>
                                    )}
                                  </td>
                                )
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          
        </div>
      </main>
    </div>
  );
}
"""

with open("index_new.tsx", "w") as f:
    f.write(content)
