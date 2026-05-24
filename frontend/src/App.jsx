import { BrowserRouter, Routes, Route } from "react-router-dom";

import Sidebar from "./components/Sidebar";

import Dashboard from "./pages/Dashboard";
import Topology from "./pages/Topology";
import Alerts from "./pages/Alerts";
import Routing from "./pages/Routing";

function App() {
  return (
    <BrowserRouter>

      <div className="flex">

        <Sidebar />

        <div className="flex-1 p-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/topology" element={<Topology />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/routing" element={<Routing />} />
          </Routes>
        </div>

      </div>

    </BrowserRouter>
  );
}

export default App;