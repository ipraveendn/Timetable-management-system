import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, Plus, Search, Edit2, Trash2, DoorOpen, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { toast } from 'react-toastify';
import { getRooms, addRoom, updateRoom, deleteRoom } from '../lib/api';
import './RoomManagement.css';

const RoomManagement = () => {
  const [rooms, setRooms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRoom, setEditingRoom] = useState(null);
  const [deleteTargetId, setDeleteTargetId] = useState(null);
  const [formData, setFormData] = useState({
    room_code: '',
    room_name: '',
    room_type: '',
    capacity: 30,
    available_days: [],
    floor: '',
    building: ''
  });
  const navigate = useNavigate();

  useEffect(() => {
    fetchRooms();
  }, []);

  const fetchRooms = async () => {
    try {
      setLoading(true);
      const response = await getRooms();
      const rows = Array.isArray(response) ? response : (response?.data || []);
      const roomsData = rows.map(r => ({
        id: r.id,
        room_code: r.room_code,
        room_name: r.room_name,
        room_type: r.room_type,
        capacity: r.capacity,
        available_days: r.available_days || [],
        floor: r.floor || '',
        building: r.building || ''
      }));
      setRooms(roomsData);
    } catch (error) {
      console.error('Error fetching rooms:', error);
      toast.error('Failed to load rooms');
      setRooms([]);
    } finally {
      setLoading(false);
    }
  };

  const filteredRooms = rooms.filter(r => 
    r.room_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    r.room_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
    r.room_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
    r.building.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleAddRoom = () => {
    setEditingRoom(null);
    setFormData({
      room_code: '',
      room_name: '',
      room_type: 'Lecture',
      capacity: 30,
      available_days: [],
      floor: '',
      building: ''
    });
    setIsModalOpen(true);
  };

  const handleEditRoom = (room) => {
    setEditingRoom(room);
    setFormData({
      room_code: room.room_code,
      room_name: room.room_name,
      room_type: room.room_type,
      capacity: room.capacity,
      available_days: room.available_days || [],
      floor: room.floor || '',
      building: room.building || ''
    });
    setIsModalOpen(true);
  };

  const handleDeleteRoom = async (id) => {
    try {
      await deleteRoom(id);
      toast.success('Room deleted successfully');
      await fetchRooms();
    } catch (error) {
      console.error('Error deleting room:', error);
      toast.error('Failed to delete room');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      if (editingRoom) {
        await updateRoom(editingRoom.id, formData);
        toast.success('Room updated successfully');
      } else {
        await addRoom(formData);
        toast.success('Room added successfully');
      }
      setIsModalOpen(false);
      fetchRooms();
    } catch (error) {
      console.error('Error saving room:', error);
      toast.error(editingRoom ? 'Failed to update room' : 'Failed to add room');
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleAvailableDaysChange = (e) => {
    const daysArray = Array.from(e.target.selectedOptions, option => option.value);
    setFormData(prev => ({
      ...prev,
      available_days: daysArray
    }));
  };

  return (
    <div className="room-management">
      <div className="page-header-section">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>
          <ChevronLeft size={20} />
          Back
        </button>
        <h1>Room Management</h1>
        <button className="btn btn-primary" onClick={handleAddRoom}>
          <Plus size={18} />
          Add Room
        </button>
      </div>

      <div className="search-bar">
        <Search size={20} />
        <input 
          type="text" 
          placeholder="Search rooms..." 
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      <div className="rooms-grid">
        {loading ? (
          <div className="loading">
            <Loader2 className="animate-spin" size={32} />
            <p>Loading rooms...</p>
          </div>
        ) : (
          <motion.div 
            className="rooms-grid"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
          >
            {filteredRooms.map((room, index) => (
              <motion.div 
                key={room.id} 
                className="room-card"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                whileHover={{ y: -5 }}
              >
                <div className="room-icon">
                  <DoorOpen size={28} />
                </div>
                <div className="room-info">
                  <h3>{room.room_name}</h3>
                  <p className="room-code">{room.room_code}</p>
                  <p className="room-type">{room.room_type}</p>
                  <p className="capacity">Capacity: {room.capacity}</p>
                  {room.building && <p className="building">{room.building}</p>}
                  {room.floor && <p className="floor">Floor: {room.floor}</p>}
                  <div className="available-days">
                    {room.available_days.length > 0 ? (
                      room.available_days.map((day, i) => (
                        <span key={i} className="day-tag">{day}</span>
                      ))
                    ) : (
                      <span className="day-tag">All Days</span>
                    )}
                  </div>
                </div>
                <div className="room-actions">
                  <button className="action-icon" onClick={() => handleEditRoom(room)}>
                    <Edit2 size={16} />
                  </button>
                  <button className="action-icon danger" onClick={() => setDeleteTargetId(room.id)}>
                    <Trash2 size={16} />
                  </button>
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}
      </div>

      {/* Add/Edit Room Modal */}
      {isModalOpen && (
        <div className="modal-overlay" onClick={() => setIsModalOpen(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h2>{editingRoom ? 'Edit Room' : 'Add Room'}</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="room_code">Room Code</label>
                <input
                  type="text"
                  id="room_code"
                  name="room_code"
                  value={formData.room_code}
                  onChange={handleInputChange}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="room_name">Room Name</label>
                <input
                  type="text"
                  id="room_name"
                  name="room_name"
                  value={formData.room_name}
                  onChange={handleInputChange}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="room_type">Room Type</label>
                <select
                  id="room_type"
                  name="room_type"
                  value={formData.room_type}
                  onChange={handleInputChange}
                >
                  <option value="Lecture">Lecture Hall</option>
                  <option value="Lab">Laboratory</option>
                  <option value="Tutorial">Tutorial Room</option>
                  <option value="Seminar">Seminar Room</option>
                  <option value="Practical">Practical Lab</option>
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="capacity">Capacity</label>
                <input
                  type="number"
                  id="capacity"
                  name="capacity"
                  min="1"
                  max="500"
                  value={formData.capacity}
                  onChange={handleInputChange}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="building">Building</label>
                <input
                  type="text"
                  id="building"
                  name="building"
                  value={formData.building}
                  onChange={handleInputChange}
                />
              </div>
              <div className="form-group">
                <label htmlFor="floor">Floor</label>
                <input
                  type="text"
                  id="floor"
                  name="floor"
                  value={formData.floor}
                  onChange={handleInputChange}
                />
              </div>
              <div className="form-group">
                <label htmlFor="available_days">Available Days</label>
                <select
                  id="available_days"
                  name="available_days"
                  multiple
                  value={formData.available_days}
                  onChange={handleAvailableDaysChange}
                  className="multi-select"
                >
                  <option value="Monday">Monday</option>
                  <option value="Tuesday">Tuesday</option>
                  <option value="Wednesday">Wednesday</option>
                  <option value="Thursday">Thursday</option>
                  <option value="Friday">Friday</option>
                  <option value="Saturday">Saturday</option>
                  <option value="Sunday">Sunday</option>
                </select>
                <small>Hold Ctrl/Cmd to select multiple days</small>
              </div>
              <div className="form-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  {editingRoom ? 'Update' : 'Add'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {deleteTargetId && (
        <div className="modal-overlay" onClick={() => setDeleteTargetId(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Delete Room</h2>
            <p>Are you sure you want to delete this room?</p>
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
                  await handleDeleteRoom(target);
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

export default RoomManagement;
