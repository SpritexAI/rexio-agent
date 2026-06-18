import { BookOpen, Code } from 'lucide-react';

interface Skill {
  name: string;
  description: string;
  code: string;
  created_at: string;
}

interface SkillsHubProps {
  skills: Skill[];
  setSelectedSkill: (skill: Skill | null) => void;
}

export default function SkillsHub({ skills, setSelectedSkill }: SkillsHubProps) {
  return (
    <div className="w-80 flex flex-col border-l border-white/[0.06] bg-[#1f1f1e] flex-shrink-0">
      {/* Header */}
      <div className="p-5 border-b border-white/[0.06] flex items-center space-x-3">
        <BookOpen size={20} className="text-[#8b5cf6]" />
        <h2 className="text-sm font-bold text-white">Dynamic Skills Hub</h2>
      </div>

      {/* Banner */}
      <div className="p-4 bg-[#8b5cf6]/5 border-b border-white/[0.06]">
        <p className="text-xs text-[#a78bfa] leading-relaxed font-sans">
          RexiO Agent dynamically compiles successful agent workflows into reusable Python functions and registers them as real-time tools.
        </p>
      </div>

      {/* Skills list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        <p className="text-xs font-semibold text-[#8a8a85] uppercase tracking-wider">Loaded Skills ({skills.length})</p>
        {skills.length === 0 ? (
          <div className="text-center py-12 text-sm text-gray-600">No custom skills compiled yet</div>
        ) : (
          skills.map((skill) => (
            <div
              key={skill.name}
              onClick={() => setSelectedSkill(skill)}
              className="p-3 bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.06] rounded-xl cursor-pointer transition-all duration-150 group"
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-mono font-bold text-[#8b5cf6] group-hover:text-[#a78bfa]">
                  {skill.name}
                </span>
                <Code size={12} className="text-gray-500 group-hover:text-gray-300" />
              </div>
              <p className="text-xs text-gray-400 line-clamp-2 leading-relaxed">{skill.description}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
