import React, { useState } from "react";

function App() {
  const [status, setStatus] = useState("");    // To show status messages like success or error
  const [user, setUser] = useState("");        // To store user input
  const [device, setDevice] = useState("");    // To store device ID input

  // Handle button click for creating the server
  const handleClick = async () => {
    if (!user || !device) {
      setStatus("Please enter User and Device ID!"); // Check if both inputs are provided
      return;
    }

    setStatus("Creating server..."); // Show status while server is being created

    try {
      // Send POST request to the backend API (Replace with your backend's IP)
      const res = await fetch("http://98.88.38.166:8000/create-server", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user: user,
          device_id: device, // Send device ID and user data to the backend
        }),
      });

      const data = await res.json(); // Parse the JSON response

      if (res.ok) {
        // Success: Update status with resource info returned from the backend
        setStatus(
          `Server Created! Device: ${data.device_id}, Resource ID: ${data.resource_id}`
        );
      } else {
        // Error: Show the error message from the backend
        setStatus(`Error: ${data.detail}`);
      }
    } catch (error) {
      // Catch any errors during the request and show the error message
      setStatus(`Error: ${error.message}`);
    }
  };

  return (
    <div style={{ textAlign: "center", marginTop: "50px" }}>
      <h1>CosmicGen AWS Server Creator</h1>

      {/* Input for User */}
      <input
        placeholder="Enter User"
        value={user}
        onChange={(e) => setUser(e.target.value)} // Update user state on change
        style={{ marginRight: "10px", padding: "5px" }}
      />

      {/* Input for Device ID */}
      <input
        placeholder="Enter Device ID"
        value={device}
        onChange={(e) => setDevice(e.target.value)} // Update device state on change
        style={{ marginRight: "10px", padding: "5px" }}
      />

      <br />
      
      {/* Button to trigger server creation */}
      <button
        onClick={handleClick} // Handle click event to call backend
        style={{ marginTop: "20px", padding: "10px 20px" }}
      >
        Create Server
      </button>

      {/* Show status of server creation */}
      <p style={{ marginTop: "20px", fontWeight: "bold" }}>{status}</p>
    </div>
  );
}

export default App;
