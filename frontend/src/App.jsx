import { Routes, Route } from "react-router-dom";

import Navbar from "./components/Navbar";

import Dashboard from "./pages/Dashboard";
import BookMachine from "./pages/BookMachine";
import TrackBooking from "./pages/TrackBooking";

function App() {
  return (
    <>
      <Navbar />

      <main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/book" element={<BookMachine />} />
          <Route path="/track" element={<TrackBooking />} />
        </Routes>
      </main>
    </>
  );
}

export default App;