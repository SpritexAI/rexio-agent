interface Skill {
  name: string;
  description: string;
  code: string;
  created_at: string;
}

interface SkillModalProps {
  selectedSkill: Skill | null;
  setSelectedSkill: (skill: Skill | null) => void;
}

export default function SkillModal({ selectedSkill, setSelectedSkill }: SkillModalProps) {
  if (!selectedSkill) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-6">
      <div className="w-full max-w-3xl bg-[#1f1f1e] border border-white/[0.08] rounded-2xl flex flex-col h-[70vh] shadow-2xl">
        {/* Header */}
        <div className="p-5 border-b border-white/[0.08] flex items-center justify-between bg-[#1f1f1e] rounded-t-2xl">
          <div>
            <h3 className="font-mono font-bold text-sm text-[#8b5cf6]">{selectedSkill.name}</h3>
            <p className="text-xs text-gray-500 mt-1">{selectedSkill.description}</p>
          </div>
          <button
            onClick={() => setSelectedSkill(null)}
            className="text-gray-400 hover:text-white transition-colors font-mono text-xs"
          >
            [Close]
          </button>
        </div>

        {/* Code View */}
        <div className="flex-1 overflow-y-auto p-5 bg-gray-950 font-mono text-xs relative">
          <pre className="text-green-400 leading-relaxed overflow-x-auto whitespace-pre-wrap select-text">
            {selectedSkill.code}
          </pre>
        </div>
      </div>
    </div>
  );
}
