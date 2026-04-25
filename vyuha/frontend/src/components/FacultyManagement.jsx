import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, Plus, Search, Edit2, Trash2, Users, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { toast } from 'react-toastify';
import { getFaculty, addFaculty, updateFaculty, deleteFaculty } from '../lib/api';
import './FacultyManagement.css';

const FacultyManagement = () => {
  const [faculty, setFaculty] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingFaculty, setEditingFaculty] = useState(null);
  const [deleteTargetId, setDeleteTargetId] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    employee_id: '',
    department: '',
    subjects: [],
    semesters: [],
    max_classes_per_day: 5,
    email: '',
    phone: ''
  });
  const navigate = useNavigate();

  useEffect(() => {
    fetchFaculty();
  }, []);

  const fetchFaculty = async () => {
    try {
      setLoading(true);
      const response = await getFaculty();
      const rows = Array.isArray(response) ? response : (response?.data || []);
      const facultyData = rows.map(f => ({
        id: f.id,
        name: f.name,
        employee_id: f.employee_id,
        email: f.email || `${f.name.toLowerCase().replace(' ', '.')}@college.edu`,
        department: f.department || 'General',
        subjects: f.subjects || [],
        semesters: f.semesters || [],
        max_classes_per_day: f.max_classes_per_day || 5,
        phone: f.phone || ''
      }));
      setFaculty(facultyData);
    } catch (error) {
      console.error('Error fetching faculty:', error);
      toast.error('Failed to load faculty');
      setFaculty([]);
    } finally {
      setLoading(false);
    }
  };

  const filteredFaculty = faculty.filter(f => 
    f.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    f.department.toLowerCase().includes(searchQuery.toLowerCase()) ||
    f.employee_id?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleAddFaculty = () => {
    setEditingFaculty(null);
    setFormData({
      name: '',
      employee_id: '',
      department: '',
      subjects: [],
      semesters: [],
      max_classes_per_day: 5,
      email: '',
      phone: ''
    });
    setIsModalOpen(true);
  };

  const handleEditFaculty = (faculty) => {
    setEditingFaculty(faculty);
    setFormData({
      name: faculty.name,
      employee_id: faculty.employee_id || '',
      department: faculty.department || 'General',
      subjects: faculty.subjects || [],
      semesters: faculty.semesters || [],
      max_classes_per_day: faculty.max_classes_per_day || 5,
      email: faculty.email || '',
      phone: faculty.phone || ''
    });
    setIsModalOpen(true);
  };

  const handleDeleteFaculty = async (id) => {
    try {
      await deleteFaculty(id);
      toast.success('Faculty deleted successfully');
      await fetchFaculty();
    } catch (error) {
      console.error('Error deleting faculty:', error);
      toast.error('Failed to delete faculty');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      if (editingFaculty) {
        await updateFaculty(editingFaculty.id, formData);
        toast.success('Faculty updated successfully');
      } else {
        await addFaculty(formData);
        toast.success('Faculty added successfully');
      }
      setIsModalOpen(false);
      fetchFaculty();
    } catch (error) {
      console.error('Error saving faculty:', error);
      toast.error(editingFaculty ? 'Failed to update faculty' : 'Failed to add faculty');
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubjectsChange = (e) => {
    const subjectsArray = e.target.value.split(',').map(s => s.trim()).filter(s => s);
    setFormData(prev => ({
      ...prev,
      subjects: subjectsArray
    }));
  };

  return (
    <div className="faculty-management">
      <div className="page-header-section">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>
          <ChevronLeft size={20} />
          Back
        </button>
        <h1>Faculty Management</h1>
        <button className="btn btn-primary" onClick={handleAddFaculty}>
          <Plus size={18} />
          Add Faculty
        </button>
      </div>

      <div className="search-bar">
        <Search size={20} />
        <input 
          type="text" 
          placeholder="Search faculty..." 
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      {loading ? (
        <div className="loading">
          <Loader2 className="animate-spin" size={32} />
          <p>Loading faculty...</p>
        </div>
      ) : (
        <motion.div 
          className="faculty-grid"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          {filteredFaculty.map((f, index) => (
            <motion.div 
              key={f.id} 
              className="faculty-card"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              whileHover={{ y: -5 }}
            >
              <div className="faculty-avatar">
                <Users size={24} />
              </div>
              <div className="faculty-info">
                <h3>{f.name}</h3>
                <p className="employee-id">ID: {f.employee_id}</p>
                <p className="department">{f.department}</p>
                <p className="email">{f.email}</p>
                <p className="phone">{f.phone}</p>
                <div className="subjects">
                  {f.subjects.map((s, i) => (
                    <span key={i} className="subject-tag">{s}</span>
                  ))}
                </div>
                <p className="max-classes">Max classes/day: {f.max_classes_per_day}</p>
              </div>
              <div className="faculty-actions">
                <button className="action-icon" onClick={() => handleEditFaculty(f)}>
                  <Edit2 size={16} />
                </button>
                <button className="action-icon danger" onClick={() => setDeleteTargetId(f.id)}>
                  <Trash2 size={16} />
                </button>
              </div>
            </motion.div>
          ))}
        </motion.div>
      )}

      {/* Add/Edit Faculty Modal */}
      {isModalOpen && (
        <div className="modal-overlay" onClick={() => setIsModalOpen(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h2>{editingFaculty ? 'Edit Faculty' : 'Add Faculty'}</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="name">Name</label>
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
                <label htmlFor="employee_id">Employee ID</label>
                <input
                  type="text"
                  id="employee_id"
                  name="employee_id"
                  value={formData.employee_id}
                  onChange={handleInputChange}
                />
              </div>
              <div className="form-group">
                <label htmlFor="department">Department</label>
                <input
                  type="text"
                  id="department"
                  name="department"
                  value={formData.department}
                  onChange={handleInputChange}
                />
              </div>
              <div className="form-group">
                <label htmlFor="email">Email</label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                />
              </div>
              <div className="form-group">
                <label htmlFor="phone">Phone</label>
                <input
                  type="text"
                  id="phone"
                  name="phone"
                  value={formData.phone}
                  onChange={handleInputChange}
                />
              </div>
              <div className="form-group">
                <label htmlFor="subjects">Subjects (comma-separated)</label>
                <input
                  type="text"
                  id="subjects"
                  value={formData.subjects.join(', ')}
                  onChange={handleSubjectsChange}
                />
              </div>
              <div className="form-group">
                <label htmlFor="max_classes_per_day">Max Classes/Day</label>
                <input
                  type="number"
                  id="max_classes_per_day"
                  name="max_classes_per_day"
                  min="1"
                  max="10"
                  value={formData.max_classes_per_day}
                  onChange={handleInputChange}
                />
              </div>
              <div className="form-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  {editingFaculty ? 'Update' : 'Add'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {deleteTargetId && (
        <div className="modal-overlay" onClick={() => setDeleteTargetId(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Delete Faculty</h2>
            <p>Are you sure you want to delete this faculty member?</p>
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
                  await handleDeleteFaculty(target);
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

export default FacultyManagement;
