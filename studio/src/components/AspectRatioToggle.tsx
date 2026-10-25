import React from 'react';
import { Smartphone, Monitor, Square } from 'lucide-react';

interface AspectRatioToggleProps {
  value: '16:9' | '9:16' | '1:1';
  onChange: (ratio: '16:9' | '9:16' | '1:1') => void;
  disabled?: boolean;
}

export const AspectRatioToggle: React.FC<AspectRatioToggleProps> = ({ value, onChange, disabled }) => {
  return (
    <div>
      <span className="label-title">Aspect Ratio Framing</span>
      <div className="aspect-selector">
        <button
          type="button"
          disabled={disabled}
          className={`aspect-btn ${value === '16:9' ? 'active' : ''}`}
          onClick={() => onChange('16:9')}
        >
          <Monitor size={18} />
          <span>16:9 YouTube</span>
        </button>

        <button
          type="button"
          disabled={disabled}
          className={`aspect-btn ${value === '9:16' ? 'active' : ''}`}
          onClick={() => onChange('9:16')}
        >
          <Smartphone size={18} />
          <span>9:16 Shorts</span>
        </button>

        <button
          type="button"
          disabled={disabled}
          className={`aspect-btn ${value === '1:1' ? 'active' : ''}`}
          onClick={() => onChange('1:1')}
        >
          <Square size={18} />
          <span>1:1 Square</span>
        </button>
      </div>
    </div>
  );
};
