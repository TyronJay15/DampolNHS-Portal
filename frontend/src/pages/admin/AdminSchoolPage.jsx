import { useEffect, useState } from 'react';
import Loading from '../../components/Loading/Loading';
import {
  createSection,
  fetchAssignments,
  fetchPlacements,
  fetchPrograms,
  fetchSchoolYears,
  fetchSections,
  fetchSubjects,
  fetchTeachers,
  saveAssignment,
  savePlacement,
} from '../../services/adminService';
import './cms/AdminCms.css';

export default function AdminSchoolPage() {
  const [years, setYears] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [sections, setSections] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [placements, setPlacements] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [sectionForm, setSectionForm] = useState({ name: '', grade_level: 'Grade 11', program: '', school_year: '' });
  const [placeForm, setPlaceForm] = useState({ student: '', section: '' });
  const [assignForm, setAssignForm] = useState({
    teacher: '',
    type: 'subject_teacher',
    section: '',
    subject: '',
  });
  const [assignSubjects, setAssignSubjects] = useState([]);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  async function load() {
    const [yearRows, programRows, sectionRows, teacherRows, placementRows, assignmentRows] =
      await Promise.all([
        fetchSchoolYears(),
        fetchPrograms(),
        fetchSections(),
        fetchTeachers(),
        fetchPlacements(),
        fetchAssignments(),
      ]);
    setYears(yearRows);
    setPrograms(programRows);
    setSections(sectionRows);
    setTeachers(teacherRows);
    setPlacements(placementRows);
    setAssignments(assignmentRows);
    const current = yearRows.find((row) => row.is_current) || yearRows[0];
    setSectionForm((form) => {
      const grade = form.grade_level || 'Grade 11';
      const gradePrograms = programRows.filter((row) => row.grade_level === grade);
      const stillValid = gradePrograms.some((row) => String(row.id) === form.program);
      return {
        ...form,
        school_year: form.school_year || (current ? String(current.id) : ''),
        program: stillValid ? form.program : gradePrograms[0] ? String(gradePrograms[0].id) : '',
      };
    });
  }

  useEffect(() => {
    load()
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const section = sections.find((row) => String(row.id) === assignForm.section);
    if (!section?.program_code) {
      setAssignSubjects([]);
      return undefined;
    }
    let cancelled = false;
    fetchSubjects(section.program_code)
      .then((rows) => {
        if (!cancelled) setAssignSubjects(rows);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [assignForm.section, sections]);

  async function handleCreateSection(event) {
    event.preventDefault();
    setError('');
    try {
      await createSection({
        name: sectionForm.name,
        grade_level: sectionForm.grade_level,
        program: Number(sectionForm.program) || null,
        school_year: Number(sectionForm.school_year),
      });
      setSectionForm((form) => ({ ...form, name: '' }));
      setMessage('Section created.');
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handlePlace(event) {
    event.preventDefault();
    setError('');
    try {
      await savePlacement({ student: Number(placeForm.student), section: Number(placeForm.section) });
      setMessage('Student placed in a section.');
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleAssign(event) {
    event.preventDefault();
    setError('');
    try {
      await saveAssignment({
        teacher: Number(assignForm.teacher),
        type: assignForm.type,
        section: assignForm.section ? Number(assignForm.section) : null,
        subject: assignForm.subject ? Number(assignForm.subject) : null,
      });
      setMessage('Teacher assignment saved.');
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  if (loading) return <Loading label="Loading school roster…" />;

  return (
    <div className="admin-school">
      <h1>School roster</h1>
      <p className="admin-lede">Create sections, place approved students, and assign subject teachers or advisers.</p>
      {message ? <p className="alert alert-info">{message}</p> : null}
      {error ? <p className="alert alert-error">{error}</p> : null}

      <form className="card admin-school-card" onSubmit={handleCreateSection}>
        <h2>New section</h2>
        <label className="form-field">
          Name
          <input
            required
            value={sectionForm.name}
            onChange={(event) => setSectionForm({ ...sectionForm, name: event.target.value })}
          />
        </label>
        <label className="form-field">
          Grade level
          <select
            value={sectionForm.grade_level}
            onChange={(event) => {
              const grade_level = event.target.value;
              const match = programs.find((row) => row.grade_level === grade_level);
              setSectionForm({
                ...sectionForm,
                grade_level,
                program: match ? String(match.id) : '',
              });
            }}
          >
            <option>Grade 11</option>
            <option>Grade 12</option>
          </select>
        </label>
        <label className="form-field">
          School year
          <select
            value={sectionForm.school_year}
            onChange={(event) => setSectionForm({ ...sectionForm, school_year: event.target.value })}
          >
            {years.map((year) => (
              <option key={year.id} value={year.id}>
                {year.label}
              </option>
            ))}
          </select>
        </label>
        <label className="form-field">
          Program
          <select
            value={sectionForm.program}
            onChange={(event) => setSectionForm({ ...sectionForm, program: event.target.value })}
          >
            {programs
              .filter((program) => program.grade_level === sectionForm.grade_level)
              .map((program) => (
                <option key={program.id} value={program.id}>
                  {program.code}
                </option>
              ))}
          </select>
        </label>
        <button className="btn" type="submit">
          Create section
        </button>
      </form>

      <form className="card admin-school-card" onSubmit={handlePlace}>
        <h2>Place student</h2>
        <label className="form-field">
          Student
          <select
            required
            value={placeForm.student}
            onChange={(event) => setPlaceForm({ ...placeForm, student: event.target.value })}
          >
            <option value="">Select student</option>
            {placements.map((row) => (
              <option key={row.student_id} value={row.student_id}>
                {row.name} ({row.lrn})
              </option>
            ))}
          </select>
        </label>
        <label className="form-field">
          Section
          <select
            required
            value={placeForm.section}
            onChange={(event) => setPlaceForm({ ...placeForm, section: event.target.value })}
          >
            <option value="">Select section</option>
            {sections.map((section) => (
              <option key={section.id} value={section.id}>
                {section.name} · {section.grade_level}
              </option>
            ))}
          </select>
        </label>
        <button className="btn" type="submit">
          Save placement
        </button>
      </form>

      <div className="card admin-school-table-wrap">
        <table className="admin-school-table">
          <thead>
            <tr>
              <th>Student</th>
              <th>LRN</th>
              <th>Section</th>
            </tr>
          </thead>
          <tbody>
            {placements.map((row) => (
              <tr key={row.student_id}>
                <td>{row.name}</td>
                <td>{row.lrn}</td>
                <td>{row.section || 'Unassigned'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <form className="card admin-school-card" onSubmit={handleAssign}>
        <h2>Assign teacher</h2>
        <label className="form-field">
          Teacher
          <select
            required
            value={assignForm.teacher}
            onChange={(event) => setAssignForm({ ...assignForm, teacher: event.target.value })}
          >
            <option value="">Select teacher</option>
            {teachers.map((teacher) => (
              <option key={teacher.id} value={teacher.id}>
                {teacher.name}
              </option>
            ))}
          </select>
        </label>
        <label className="form-field">
          Type
          <select
            value={assignForm.type}
            onChange={(event) => setAssignForm({ ...assignForm, type: event.target.value })}
          >
            <option value="subject_teacher">Subject teacher</option>
            <option value="adviser">Adviser</option>
          </select>
        </label>
        <label className="form-field">
          Section
          <select
            value={assignForm.section}
            onChange={(event) =>
              setAssignForm({ ...assignForm, section: event.target.value, subject: '' })
            }
          >
            <option value="">None</option>
            {sections.map((section) => (
              <option key={section.id} value={section.id}>
                {section.name}
              </option>
            ))}
          </select>
        </label>
        <label className="form-field">
          Subject
          <select
            value={assignForm.subject}
            onChange={(event) => setAssignForm({ ...assignForm, subject: event.target.value })}
          >
            <option value="">None</option>
            {assignSubjects.map((subject) => (
              <option key={subject.id} value={subject.id}>
                {subject.name}
              </option>
            ))}
          </select>
        </label>
        <button className="btn" type="submit">
          Save assignment
        </button>
      </form>

      <div className="card admin-school-table-wrap">
        <table className="admin-school-table">
          <thead>
            <tr>
              <th>Teacher</th>
              <th>Type</th>
              <th>Section</th>
              <th>Subject</th>
            </tr>
          </thead>
          <tbody>
            {assignments.map((row) => (
              <tr key={row.id}>
                <td>{row.teacher}</td>
                <td>{row.type.replace('_', ' ')}</td>
                <td>{row.section || '—'}</td>
                <td>{row.subject || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
