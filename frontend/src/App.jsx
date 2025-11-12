import React, { useState } from "react";

function App() {
  const [status, setStatus] = useState("");
  const [user, setUser] = useState("");
  const [device, setDevice] = useState("");

  const handleClick = async () => {
    if (!user || !device) {
      setStatus("Please enter User and Device ID!");
      return;
    }

    setStatus("Creating server...");

    try {
      const res = await fetch("http://98.88.38.166:8000/create-server", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user: user,
          device_id: device,
        }),
      });

      const data = await res.json();
      if (res.ok) {
        setStatus(
          `Server Created! Device: ${data.device_id}, Resource ID: ${data.resource_id}`
        );
      } else {
        setStatus(`Error: ${data.detail}`);
      }
    } catch (error) {
      setStatus(`Error: ${error.message}`);
    }
  };

  return (
    <div style={{ textAlign: "center", marginTop: "50px" }}>
      <h1>CosmicGen AWS Server Creator</h1>
      <input
        placeholder="Enter User"
        value={user}
        onChange={(e) => setUser(e.target.value)}
        style={{ marginRight: "10px", padding: "5px" }}
      />
      <input
        placeholder="Enter Device ID"
        value={device}
        onChange={(e) => setDevice(e.target.value)}
        style={{ marginRight: "10px", padding: "5px" }}
      />
      <br />
      <button
        onClick={handleClick}
        style={{ marginTop: "20px", padding: "10px 20px" }}
      >
        Create Server
      </button>
      <p style={{ marginTop: "20px", fontWeight: "bold" }}>{status}</p>
    </div>
  );
}

export default App;
