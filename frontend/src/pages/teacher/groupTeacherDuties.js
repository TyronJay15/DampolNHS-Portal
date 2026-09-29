export function groupByProgramSection(rows) {
  const programs = new Map();

  for (const row of rows) {
    const programKey = row.program_code || 'General';
    if (!programs.has(programKey)) {
      programs.set(programKey, { code: programKey, sections: new Map() });
    }
    const program = programs.get(programKey);
    const sectionKey = row.section || row.section_name || 'Unknown section';
    if (!program.sections.has(sectionKey)) {
      program.sections.set(sectionKey, {
        name: sectionKey,
        grade_level: row.grade_level,
        school_year: row.school_year,
        tasks: [],
      });
    }
    program.sections.get(sectionKey).tasks.push(row);
  }

  return [...programs.values()].map((program) => ({
    code: program.code,
    sections: [...program.sections.values()].sort((a, b) => a.name.localeCompare(b.name)),
  }));
}

export function openAllGroups(programs, sectionPrefix = '') {
  const programsOpen = {};
  const sectionsOpen = {};
  programs.forEach((program) => {
    programsOpen[program.code] = true;
    program.sections.forEach((section) => {
      sectionsOpen[`${sectionPrefix}${program.code}-${section.name}`] = true;
    });
  });
  return { programsOpen, sectionsOpen };
}
