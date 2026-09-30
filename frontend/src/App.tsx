import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { TopBar } from './components/TopBar';
import { Landing } from './screens/Landing';
import { Card } from './screens/Card';
import { Controls } from './screens/Controls';
import { Describe } from './screens/Describe';
import { Evidence } from './screens/Evidence';
import { Test } from './screens/Test';

export function App() {
  return (
    <BrowserRouter>
      <TopBar />
      <main>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/overview" element={<Landing />} />
          <Route path="/describe" element={<Describe />} />
          <Route path="/card" element={<Card />} />
          <Route path="/controls" element={<Controls />} />
          <Route path="/test" element={<Test />} />
          <Route path="/evidence" element={<Evidence />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}
