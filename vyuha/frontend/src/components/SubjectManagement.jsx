import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, Plus, BookOpen, Search, Edit2, Trash2, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { toast } from 'react-toastify';
import { getSubjects, addSubject, updateSubject, deleteSubject } from '../lib/api';
import './SubjectManagement.css';

const SubjectManagement = () => {
  const [subjects, setSubjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingSubject, setEditingSubject] = useState(null);
  const [deleteTargetId, setDeleteTargetId] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    code: '',
    semester: '',
    classes_per_week: '',
    room_type_required: '',
    duration_minutes: 60
  });
  const navigate = useNavigate();

  useEffect(() => {
    fetchSubjects();
  }, []);

  const fetchSubjects = async () => {
    try {
      setLoading(true);
      const response = await getSubjects();
      const rows = Array.isArray(response) ? response : (response?.data || []);
      const subjectsData = rows.map(s => ({
        id: s.id,
        name: s.name,
        code: s.code,
        semester: s.semester,
        classes_per_week: s.classes_per_week,
        room_type_required: s.room_type_required,
        duration_minutes: s.duration_minutes
      }));
      setSubjects(subjectsData);
    } catch (error) {
      console.error('Error fetching subjects:', error);
      toast.error('Failed to load subjects');
      setSubjects([]);
    } finally {
      setLoading(false);
    }
  };

  const filteredSubjects = subjects.filter(s => 
    s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.semester.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleAddSubject = () => {
    setEditingSubject(null);
    setFormData({
      name: '',
      code: '',
      semester: '',
      classes_per_week: '',
      room_type_required: '',
      duration_minutes: 60
    });
    setIsModalOpen(true);
  };

  const handleEditSubject = (subject) => {
    setEditingSubject(subject);
    setFormData({
      name: subject.name,
      code: subject.code,
      semester: subject.semester,
      classes_per_week: subject.classes_per_week,
      room_type_required: subject.room_type_required,
      duration_minutes: subject.duration_minutes
    });
    setIsModalOpen(true);
  };

  const handleDeleteSubject = async (id) => {
    try {
      await deleteSubject(id);
      toast.success('Subject deleted successfully');
      await fetchSubjects();
    } catch (error) {
      console.error('Error deleting subject:', error);
      toast.error('Failed to delete subject');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      if (editingSubject) {
        await updateSubject(editingSubject.id, formData);
        toast.success('Subject updated successfully');
      } else {
        await addSubject(formData);
        toast.success('Subject added successfully');
      }
      setIsModalOpen(false);
      fetchSubjects();
    } catch (error) {
      console.error('Error saving subject:', error);
      toast.error(editingSubject ? 'Failed to update subject' : 'Failed to add subject');
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  return (
    <div className="subject-management">
      <div className="page-header-section">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>
          <ChevronLeft size={20} />
          Back
        </button>
        <h1>Subject Management</h1>
        <button className="btn btn-primary" onClick={handleAddSubject}>
          <Plus size={18} />
          Add Subject
        </button>
      </div>

      <div className="search-bar">
        <Search size={20} />
        <input 
          type="text" 
          placeholder="Search subjects..." 
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      <div className="subjects-list">
        {loading ? (
          <div className="loading">
            <Loader2 className="animate-spin" size={32} />
            <p>Loading subjects...</p>
          </div>
        ) : (
          <motion.div 
            className="subjects-list"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
          >
            {filteredSubjects.map((subject, index) => (
              <motion.div 
                key={subject.id} 
                className="subject-card"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                whileHover={{ y: -5 }}
              >
                <div className="subject-icon">
                  <BookOpen size={24} />
                </div>
                <div className="subject-info">
                  <h3>{subject.name}</h3>
                  <p className="subject-code">{subject.code}</p>
                  <p className="subject-detail">
                    Semester {subject.semester} • {subject.classes_per_week} classes/week
                  </p>
                  <p className="subject-detail">
                    Room: {subject.room_type_required || 'Any'} • Duration: {subject.duration_minutes} min
                  </p>
                </div>
                <div className="subject-actions">
                  <button className="action-icon" onClick={() => handleEditSubject(subject)}>
                    <Edit2 size={16} />
                  </button>
                  <button className="action-icon danger" onClick={() => setDeleteTargetId(subject.id)}>
                    <Trash2 size={16} />
                  </button>
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}
      </div>

      {/* Add/Edit Subject Modal */}
      {isModalOpen && (
        <div className="modal-overlay" onClick={() => setIsModalOpen(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h2>{editingSubject ? 'Edit Subject' : 'Add Subject'}</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="name">Subject Name</label>
                <input
                  type="text"
                  id="name"
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="code">Subject Code</label>
                <input
                  type="text"
                  id="code"
                  name="code"
                  value={formData.code}
                  onChange={handleInputChange}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="semester">Semester</label>
                <select
                  id="semester"
                  name="semester"
                  value={formData.semester}
                  onChange={handleInputChange}
                  required
                >
                  <option value="">Select Semester</option>
                  <option value="1">Semester 1</option>
                  <option value="2">Semester 2</option>
                  <option value="3">Semester 3</option>
                  <option value="4">Semester 4</option>
                  <option value="5">Semester 5</option>
                  <option value="6">Semester 6</option>
                  <option value="7">Semester 7</option>
                  <option value="8">Semester 8</option>
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="classes_per_week">Classes Per Week</label>
                <input
                  type="number"
                  id="classes_per_week"
                  name="classes_per_week"
                  min="1"
                  max="10"
                  value={formData.classes_per_week}
                  onChange={handleInputChange}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="room_type_required">Room Type Required</label>
                <select
                  id="room_type_required"
                  name="room_type_required"
                  value={formData.room_type_required}
                  onChange={handleInputChange}
                >
                  <option value="">Any</option>
                  <option value="Lecture">Lecture Hall</option>
                  <option value="Lab">Laboratory</option>
                  <option value="Tutorial">Tutorial Room</option>
                  <option value="Seminar">Seminar Room</option>
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="duration_minutes">Duration (minutes)</label>
                <input
                  type="number"
                  id="duration_minutes"
                  name="duration_minutes"
                  min="30"
                  max="180"
                  step="15"
                  value={formData.duration_minutes}
                  onChange={handleInputChange}
                  required
                />
              </div>
              <div className="form-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  {editingSubject ? 'Update' : 'Add'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {deleteTargetId && (
        <div className="modal-overlay" onClick={() => setDeleteTargetId(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Delete Subject</h2>
            <p>Are you sure you want to delete this subject?</p>
            <div className="form-actions">
              <button type="button" className="btn btn-secondary" onClick={() => setDeleteTargetId(null)}>
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-danger"
                onClick={async () => {
                  const target = deleteTargetId;
                  setDeleteTargetId(null);
                  await handleDeleteSubject(target);
                }}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SubjectManagement;
