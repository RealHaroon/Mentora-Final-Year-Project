"use client";

import { useCallback, useEffect, useState } from "react";

const SLIDES = [
  {
    image: "/carousel/timetable.svg",
    alt: "Weekly AI study timetable with weak topics highlighted",
    caption: "AI-generated timetable adapts daily to your exam date, weak topics & available hours",
  },
  {
    image: "/carousel/career.svg",
    alt: "Ranked list of career fits with match percentages",
    caption: "Upload your CV and get ranked career fits with a 6-month roadmap to close your skill gaps",
  },
  {
    image: "/carousel/playlists.svg",
    alt: "Video player with an auto-curated topic playlist",
    caption: "Auto-curated YouTube playlists for every topic, added to your learning portal after each session",
  },
  {
    image: "/carousel/mcq.svg",
    alt: "Adaptive multiple-choice question with a detected knowledge gap",
    caption: "Adaptive MCQ tests flag your knowledge gaps instantly so you know what to revise next",
  },
];

const AUTO_ADVANCE_MS = 2500; // 2.5 seconds per slide

export default function HeroCarousel() {
  const [index, setIndex] = useState(0);

  const goTo = useCallback((i: number) => {
    setIndex((i + SLIDES.length) % SLIDES.length);
  }, []);

  useEffect(() => {
    const timer = setInterval(() => setIndex((i) => (i + 1) % SLIDES.length), AUTO_ADVANCE_MS);
    return () => clearInterval(timer);
  }, [index]); // restarts the timer after a manual click so slides never skip

  return (
    <div
      className="hero-carousel"
      role="region"
      aria-roledescription="carousel"
      aria-label="Mentora features"
    >
      <div className="carousel-viewport">
        <div className="carousel-track" style={{ transform: `translateX(-${index * 100}%)` }}>
          {SLIDES.map((slide, i) => (
            <div
              className="carousel-slide"
              key={slide.image}
              role="group"
              aria-roledescription="slide"
              aria-label={`${i + 1} of ${SLIDES.length}`}
              aria-hidden={i !== index}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={slide.image} alt={slide.alt} draggable={false} />
            </div>
          ))}
        </div>
        <button
          type="button"
          className="carousel-arrow carousel-prev"
          aria-label="Previous slide"
          onClick={() => goTo(index - 1)}
        >
          ‹
        </button>
        <button
          type="button"
          className="carousel-arrow carousel-next"
          aria-label="Next slide"
          onClick={() => goTo(index + 1)}
        >
          ›
        </button>
      </div>

      <p aria-live="polite">{SLIDES[index].caption}</p>

      <div className="carousel-dots">
        {SLIDES.map((slide, i) => (
          <button
            type="button"
            key={slide.image}
            className={i === index ? "active" : undefined}
            aria-label={`Go to slide ${i + 1}`}
            aria-current={i === index}
            onClick={() => goTo(i)}
          />
        ))}
      </div>
    </div>
  );
}
