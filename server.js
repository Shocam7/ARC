const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: { origin: '*' },
  transports: ['websocket', 'polling']
});

app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json());

// In-memory room store
// rooms[roomId] = { users: { socketId: { id, name, role } } }
const rooms = {};

function generateRoomCode() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  let code = '';
  for (let i = 0; i < 9; i++) {
    if (i === 3 || i === 6) code += '-';
    code += chars[Math.floor(Math.random() * chars.length)];
  }
  return code;
}

// REST: create a new room
app.post('/api/create-room', (req, res) => {
  const roomId = generateRoomCode();
  rooms[roomId] = { users: {} };
  res.json({ roomId });
});

// REST: check if room exists
app.get('/api/room/:roomId', (req, res) => {
  const { roomId } = req.params;
  const id = roomId.toUpperCase();
  if (rooms[id]) {
    const userList = Object.values(rooms[id].users);
    res.json({ exists: true, userCount: userList.length, users: userList });
  } else {
    res.json({ exists: false });
  }
});

io.on('connection', (socket) => {
  console.log(`Socket connected: ${socket.id}`);

  // Join a room
  socket.on('join-room', ({ roomId, name, role }) => {
    const id = roomId.toUpperCase();

    // Auto-create room if it doesn't exist
    if (!rooms[id]) {
      rooms[id] = { users: {} };
    }

    // Check if there's already a world sharer
    if (role === 'world') {
      const existingWorld = Object.values(rooms[id].users).find(u => u.role === 'world');
      if (existingWorld) {
        socket.emit('error', { message: 'A world is already being shared in this room.' });
        return;
      }
    }

    // Add user to room
    rooms[id].users[socket.id] = {
      id: socket.id,
      name: name || 'Guest',
      role: role || 'guest'
    };

    socket.join(id);
    socket.currentRoom = id;

    // Send existing users to the newcomer
    const existingUsers = Object.values(rooms[id].users).filter(u => u.id !== socket.id);
    socket.emit('room-joined', {
      roomId: id,
      userId: socket.id,
      users: existingUsers
    });

    // Notify others
    socket.to(id).emit('user-joined', {
      userId: socket.id,
      name: rooms[id].users[socket.id].name,
      role: rooms[id].users[socket.id].role
    });

    console.log(`${name} (${role}) joined room ${id}. Total: ${Object.keys(rooms[id].users).length}`);
  });

  // WebRTC signaling relay
  socket.on('signal', ({ to, signal }) => {
    io.to(to).emit('signal', {
      from: socket.id,
      signal
    });
  });

  // Disconnect
  socket.on('disconnect', () => {
    const roomId = socket.currentRoom;
    if (roomId && rooms[roomId]) {
      const user = rooms[roomId].users[socket.id];
      delete rooms[roomId].users[socket.id];

      socket.to(roomId).emit('user-left', {
        userId: socket.id,
        role: user?.role
      });

      // Clean up empty rooms
      if (Object.keys(rooms[roomId].users).length === 0) {
        delete rooms[roomId];
        console.log(`Room ${roomId} deleted (empty)`);
      }
    }
    console.log(`Socket disconnected: ${socket.id}`);
  });
});

const PORT = process.env.PORT || 8080;
server.listen(PORT, () => {
  console.log(`ARC server running on port ${PORT}`);
});
