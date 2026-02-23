import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import histogramImg from "../assets/new-logo-histogram.png";
import waveImg from "../assets/new-logo-wave.png";
import "../styles/LogoSplash.css";

interface LogoSplashProps {
  onAnimationEnd: () => void;
}

export const LogoSplash: React.FC<LogoSplashProps> = ({ onAnimationEnd }) => {
  const [isVisible, setIsVisible] = useState(true);
  const navigate = useNavigate();

  const handleWaveAnimationEnd = () => {
    // Wave animation ends, close splash
    setIsVisible(false);
  };

  useEffect(() => {
    if (!isVisible) {
      onAnimationEnd();
      navigate("/", { replace: true });
    }
  }, [isVisible, navigate, onAnimationEnd]);

  if (!isVisible) {
    return null;
  }

  return (
    <div className="logo-splash-overlay">
      <div className="logo-splash-container">
        {/* Histogram element - displays first */}
        <img
          src={histogramImg}
          alt="histogram"
          className="logo-splash-element logo-splash-histogram"
        />
        {/* Wave element - animates after histogram, triggers end on animation end */}
        <img
          src={waveImg}
          alt="wave"
          className="logo-splash-element logo-splash-wave"
          onAnimationEnd={handleWaveAnimationEnd}
        />
      </div>
    </div>
  );
};
