import { useState, useEffect } from 'react';
import { X, Plus, Trash2, Check, BookOpen, Code, Clock } from 'lucide-react';

interface CompiledSkill {
  name: string;
  description: string;
  code: string;
  status: string;
  created_at: string;
}

interface MarkdownSkill {
  name: string;
  description: string;
  content: string;
}

const BACKEND_URL = window.location.port === '5173'
  ? 'http://localhost:51730'
  : window.location.origin;

type Tab = 'markdown' | 'active' | 'pending';

export default function SkillsHub({ onClose }: { onClose: () => void }) {
  const [tab, setTab] = useState<Tab>('markdown');
  const [mdSkills, setMdSkills] = useState<MarkdownSkill[]>([]);
  const [activeSkills, setActiveSkills] = useState<CompiledSkill[]>([]);
  const [pendingSkills, setPendingSkills] = useState<CompiledSkill[]>([]);

  // Add markdown skill form
  const [showForm, setShowForm] = useState(false);
  const [formName, setFormName] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [formContent, setFormContent] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => { fetchAll(); }, []);

  async function fetchAll() {
    try {
      const [mdRes, allRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/markdown-skills`),
        fetch(`${BACKEND_URL}/api/skills`),
      ]);
      const mdData = await mdRes.json();
      const allData = await allRes.json();
      setMdSkills(mdData.skills || []);
      setActiveSkills((allData.skills || []).filter((s: CompiledSkill) => s.status === 'active'));
      setPendingSkills((allData.skills || []).filter((s: CompiledSkill) => s.status === 'pending'));
    } catch {}
  }

  async function deleteMdSkill(name: string) {
    await fetch(`${BACKEND_URL}/api/markdown-skills/${name}`, { method: 'DELETE' });
    fetchAll();
  }

  async function approveSkill(name: string) {
    await fetch(`${BACKEND_URL}/api/skills/${name}/approve`, { method: 'POST' });
    fetchAll();
  }

  async function rejectSkill(name: string) {
    await fetch(`${BACKEND_URL}/api/skills/${name}/reject`, { method: 'POST' });
    fetchAll();
  }

  async function saveMdSkill() {
    if (!formName.trim() || !formContent.trim()) return;
    setSaving(true);
    await fetch(`${BACKEND_URL}/api/markdown-skills`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: formName.trim(), description: formDesc.trim(), content: formContent.trim() }),
    });
    setSaving(false);
    setFormName(''); setFormDesc(''); setFormContent('');
    setShowForm(false);
    fetchAll();
  }

  const tabs: { key: Tab; label: string; count: number }[] = [
    { key: 'markdown', label: 'Markdown', count: mdSkills.length },
    { key: 'active',   label: 'Active',   count: activeSkills.length },
    { key: 'pending',  label: 'Pending',  count: pendingSkills.length },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={onClose}>
      <div
        className="bg-[#1a1a1a] border border-white/[0.08] rounded-2xl w-full max-w-2xl max-h-[80vh] flex flex-col shadow-2xl"
        onClick={e => e.stopPropagation()}
        style={{ animation: 'rexio-fadein 0.2s ease-out' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.07] flex-shrink-0">
          <div className="flex items-center gap-2.5">
            <BookOpen size={17} className="text-[#a78bfa]" />
            <h2 className="text-white font-semibold text-sm">Skills Hub</h2>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">
            <X size={18} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 px-5 pt-3 flex-shrink-0">
          {tabs.map(t => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
                tab === t.key
                  ? 'bg-[#8b5cf6]/15 text-[#a78bfa] border border-[#8b5cf6]/30'
                  : 'text-[#666] hover:text-gray-300'
              }`}
            >
              {t.key === 'markdown' && <BookOpen size={11} />}
              {t.key === 'active'   && <Code size={11} />}
              {t.key === 'pending'  && <Clock size={11} />}
              {t.label}
              {t.count > 0 && (
                <span className="bg-white/[0.08] text-gray-400 rounded-full px-1.5 py-0.5 text-[10px]">
                  {t.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3 custom-scrollbar">

          {/* ── Markdown Tab ── */}
          {tab === 'markdown' && (
            <>
              <p className="text-xs text-[#555] leading-relaxed">
                Instruction-based skills injected into the agent's system prompt. Write in Markdown.
              </p>

              {!showForm ? (
                <button
                  onClick={() => setShowForm(true)}
                  className="flex items-center gap-2 text-xs text-[#8b5cf6] hover:text-[#a78bfa] transition-colors"
                >
                  <Plus size={13} /> Add skill
                </button>
              ) : (
                <div className="bg-white/[0.03] border border-white/[0.07] rounded-xl p-4 space-y-3">
                  <input
                    value={formName}
                    onChange={e => setFormName(e.target.value)}
                    placeholder="Skill name (snake_case)"
                    className="w-full bg-black/30 border border-white/[0.07] rounded-lg px-3 py-2 text-xs text-white placeholder-gray-600 outline-none focus:border-[#8b5cf6]/50"
                  />
                  <input
                    value={formDesc}
                    onChange={e => setFormDesc(e.target.value)}
                    placeholder="Short description"
                    className="w-full bg-black/30 border border-white/[0.07] rounded-lg px-3 py-2 text-xs text-white placeholder-gray-600 outline-none focus:border-[#8b5cf6]/50"
                  />
                  <textarea
                    value={formContent}
                    onChange={e => setFormContent(e.target.value)}
                    placeholder="## Skill Instructions&#10;Write your instructions in Markdown..."
                    rows={6}
                    className="w-full bg-black/30 border border-white/[0.07] rounded-lg px-3 py-2 text-xs text-white placeholder-gray-600 outline-none focus:border-[#8b5cf6]/50 font-mono resize-none"
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={saveMdSkill}
                      disabled={saving}
                      className="px-3 py-1.5 bg-[#8b5cf6]/20 border border-[#8b5cf6]/40 text-[#a78bfa] text-xs rounded-lg hover:bg-[#8b5cf6]/30 transition-all"
                    >
                      {saving ? 'Saving...' : 'Save'}
                    </button>
                    <button
                      onClick={() => setShowForm(false)}
                      className="px-3 py-1.5 text-gray-500 text-xs hover:text-white transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {mdSkills.length === 0 ? (
                <p className="text-xs text-[#444] py-6 text-center">No markdown skills yet</p>
              ) : (
                mdSkills.map(s => (
                  <div key={s.name} className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-3.5">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-xs font-mono font-bold text-[#a78bfa]">{s.name}</p>
                        {s.description && <p className="text-xs text-gray-500 mt-0.5">{s.description}</p>}
                      </div>
                      <button onClick={() => deleteMdSkill(s.name)} className="text-gray-600 hover:text-red-400 transition-colors flex-shrink-0">
                        <Trash2 size={13} />
                      </button>
                    </div>
                    <pre className="mt-2 text-[11px] text-gray-500 font-mono whitespace-pre-wrap line-clamp-3 leading-relaxed">
                      {s.content}
                    </pre>
                  </div>
                ))
              )}
            </>
          )}

          {/* ── Active Tab ── */}
          {tab === 'active' && (
            <>
              <p className="text-xs text-[#555]">Approved compiled Python tools — available to the agent.</p>
              {activeSkills.length === 0 ? (
                <p className="text-xs text-[#444] py-6 text-center">No active compiled skills</p>
              ) : (
                activeSkills.map(s => (
                  <div key={s.name} className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-3.5">
                    <p className="text-xs font-mono font-bold text-green-400">{s.name}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{s.description}</p>
                    <pre className="mt-2 text-[11px] text-gray-600 font-mono whitespace-pre-wrap line-clamp-4">
                      {s.code}
                    </pre>
                  </div>
                ))
              )}
            </>
          )}

          {/* ── Pending Tab ── */}
          {tab === 'pending' && (
            <>
              <p className="text-xs text-[#555]">Compiled skills awaiting your approval before activation.</p>
              {pendingSkills.length === 0 ? (
                <p className="text-xs text-[#444] py-6 text-center">No pending skills</p>
              ) : (
                pendingSkills.map(s => (
                  <div key={s.name} className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-3.5">
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div>
                        <p className="text-xs font-mono font-bold text-yellow-400">{s.name}</p>
                        <p className="text-xs text-gray-500 mt-0.5">{s.description}</p>
                      </div>
                      <div className="flex gap-2 flex-shrink-0">
                        <button
                          onClick={() => approveSkill(s.name)}
                          className="flex items-center gap-1 px-2.5 py-1 bg-green-500/10 border border-green-500/30 text-green-400 text-[11px] rounded-lg hover:bg-green-500/20 transition-all"
                        >
                          <Check size={11} /> Approve
                        </button>
                        <button
                          onClick={() => rejectSkill(s.name)}
                          className="flex items-center gap-1 px-2.5 py-1 bg-red-500/10 border border-red-500/30 text-red-400 text-[11px] rounded-lg hover:bg-red-500/20 transition-all"
                        >
                          <Trash2 size={11} /> Reject
                        </button>
                      </div>
                    </div>
                    <pre className="text-[11px] text-gray-600 font-mono whitespace-pre-wrap line-clamp-5 bg-black/20 p-2 rounded-lg">
                      {s.code}
                    </pre>
                  </div>
                ))
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
