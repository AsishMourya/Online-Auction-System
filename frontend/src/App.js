import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Home from "./components/Home";
import AuctionDetails from "./components/AuctionDetails";
import CreateAuction from "./components/CreateAuction";
import Profile from "./components/Profile";
import Navbar from "./components/Navbar";

function App() {
  return (
    <Router>
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/auction/:id" element={<AuctionDetails />} />
        <Route path="/create" element={<CreateAuction />} />
        <Route path="/profile" element={<Profile />} />
      </Routes>
    </Router>
  );
}

export default App;
