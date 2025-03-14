import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Home from "./components/Home";
import AuctionDetails from "./components/AuctionDetails";
import CreateAuction from "./components/CreateAuction";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/auction/:id" element={<AuctionDetails />} />
        <Route path="/create" element={<CreateAuction />} />
      </Routes>
    </Router>
  );
}

export default App;
