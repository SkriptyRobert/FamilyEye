
import React from 'react';
import './VideoGuide.css';

const VideoGuide = () => {
    return (
        <section className="video-guide-section" id="tutorials">
            <div className="container">
                <h2>Video Návody</h2>
                <p className="section-subtitle">Krok za krokem instalací a nastavením</p>

                <div className="video-grid">
                    <div className="video-card">
                        <h3>Instalace & Párování</h3>
                        <div className="video-wrapper">
                            <iframe
                                src="https://www.youtube.com/embed/BrHlermdJI4"
                                title="FamilyEye | Installation & Pairing Guide"
                                frameBorder="0"
                                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                                allowFullScreen
                            ></iframe>
                        </div>
                        <p>Kompletní průvodce pro Windows a Android.</p>
                    </div>

                    <div className="video-card">
                        <h3>Docker Instalace</h3>
                        <div className="video-wrapper">
                            <iframe
                                src="https://www.youtube.com/embed/40gVGDhg9BU"
                                title="FamilyEye | Docker Install"
                                frameBorder="0"
                                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                                allowFullScreen
                            ></iframe>
                        </div>
                        <p>Rychlá instalace serveru pomocí Dockeru.</p>
                    </div>
                </div>
            </div>
        </section>
    );
};

export default VideoGuide;
