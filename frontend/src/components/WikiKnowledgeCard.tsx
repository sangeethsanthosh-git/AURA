import React, { useState, useMemo, useEffect } from 'react';
import type { WikiResult, WikiGenre, CompanionType } from '../types';

interface WikiKnowledgeCardProps {
  wiki: WikiResult;
  companion?: CompanionType;
}

const getProxyImageUrl = (rawUrl: string): string => {
  if (!rawUrl) return '';
  if (typeof window !== 'undefined' && window.location.port === '8000') {
    return `/api/wiki-image?url=${encodeURIComponent(rawUrl)}`;
  }
  return `http://127.0.0.1:8000/api/wiki-image?url=${encodeURIComponent(rawUrl)}`;
};

/**
 * Intelligent genre detection based on article title, extract, and search query.
 */
function detectGenre(title: string, extract: string, query: string): 'biography' | 'landmark' | 'archival' | 'folio' {
  const text = `${title} ${extract} ${query}`.toLowerCase();

  // 1. Landmark / Architectural Monuments / Places
  const landmarkMatches = [
    'mausoleum', 'monument', 'temple', 'cathedral', 'mosque', 'palace',
    'castle', 'pyramid', 'tower', 'bridge', 'citadel', 'building',
    'located on the', 'located in', 'situated on', 'situated in',
    'architectural', 'built by', 'commissioned in', 'unesco world heritage'
  ];
  if (landmarkMatches.some((w) => text.includes(w))) {
    return 'landmark';
  }

  // 2. Biography / People / Creators
  const bioMatches = [
    'was an american', 'was a british', 'was an english', 'was a french', 'was a japanese',
    'was an indian', 'was a german', 'was an italian', 'was an artist', 'was a writer',
    'was an author', 'was a director', 'was an animator', 'was a physicist', 'was a scientist',
    'was a politician', 'was an emperor', 'was a king', 'was a queen', 'was a general',
    'was a composer', 'is an american', 'is an artist', 'is a director', 'is an author',
    'born ', 'died ', 'known by his pen name', 'known by her pen name'
  ];
  if (bioMatches.some((w) => text.includes(w)) || /\((?:1\d{3}|20\d{2})[–—-](?:1\d{3}|20\d{2}|present)\)/.test(extract)) {
    return 'biography';
  }

  // 3. Archival / Museum Artifacts / Historical Documents / Currencies
  const archivalMatches = [
    'history of', 'dollar', 'currency', 'banknote', 'coin', 'treaty',
    'declaration', 'statute', 'constitution', 'charter', 'artifact',
    'specimen', 'manuscript', 'roman empire', 'war of', 'battle of'
  ];
  if (archivalMatches.some((w) => text.includes(w))) {
    return 'archival';
  }

  // 4. Folio / Art & Prints / Nature / Concepts
  return 'folio';
}

/**
 * Extract life dates or construction era from extract.
 */
function extractEraOrDates(extract: string): string | null {
  // Matches (November 30, 1835 - April 21, 1910) or (1835-1910) or (born 1941)
  const dateMatch = extract.match(/\((?:born\s+)?([A-Za-z]+ \d{1,2}, \d{4}|\d{4})\s*[–—-]\s*([A-Za-z]+ \d{1,2}, \d{4}|\d{4}|present)\)/i);
  if (dateMatch) {
    return `${dateMatch[1]} — ${dateMatch[2]}`;
  }
  const bornMatch = extract.match(/\(born\s+([A-Za-z]+ \d{1,2}, \d{4}|\d{4})\)/i);
  if (bornMatch) {
    return `b. ${bornMatch[1]}`;
  }
  const commMatch = extract.match(/(?:commissioned|built|completed|constructed)\s+in\s+(\d{4})/i);
  if (commMatch) {
    return `Est. ${commMatch[1]}`;
  }
  return null;
}

/**
 * Extract location or region from extract.
 */
function extractLocation(extract: string): string | null {
  const locMatch = extract.match(/(?:located|situated)\s+(?:on|in|at)\s+([A-Za-z0-9\s,–-]+?)(?:\.|\;|\, and|\, set)/i);
  if (locMatch && locMatch[1].length < 60) {
    return locMatch[1].trim();
  }
  return null;
}

/**
 * Extract category or epithet from extract.
 */
function extractEpithet(title: string, extract: string): string {
  // Strip parentheses content for cleaner parsing
  const clean = extract.replace(/\([^)]*\)/g, '').trim();
  const match = clean.match(new RegExp(`${title}[^,]*,?\\s+(?:is|was)\\s+(?:an?|the)\\s+([^.,;]+)`, 'i'));
  if (match && match[1].length < 75) {
    const raw = match[1].trim();
    return raw.charAt(0).toUpperCase() + raw.slice(1);
  }
  return 'Encyclopedic Archive';
}

/**
 * Extract a pull-quote sentence from extract.
 */
function extractPullQuote(extract: string): string | null {
  const quoteMatch = extract.match(/["“]([^"”]{20,160})["”]/);
  if (quoteMatch) {
    return quoteMatch[1];
  }
  // Fallback to second or third interesting sentence
  const sentences = extract.split(/(?<=[.!?])\s+/).filter((s) => s.length > 30 && s.length < 150);
  if (sentences.length > 1) {
    return sentences[1].replace(/^\w/, (c) => c.toUpperCase());
  }
  return null;
}

export const WikiKnowledgeCard: React.FC<WikiKnowledgeCardProps> = ({ wiki, companion = 'ember' }) => {
  const [selectedGenre, setSelectedGenre] = useState<WikiGenre>('auto');
  const [brokenUrls, setBrokenUrls] = useState<Record<string, boolean>>({});
  const [activeLightboxIdx, setActiveLightboxIdx] = useState<number | null>(null);
  const [isExpanded, setIsExpanded] = useState<boolean>(false);

  const mainArticle = wiki.articles[0] || {
    title: wiki.query,
    url: `https://en.wikipedia.org/wiki/${encodeURIComponent(wiki.query.replace(/\s+/g, '_'))}`,
    extract: 'Comprehensive encyclopedic information retrieved from Wikipedia.',
  };

  const detected = useMemo(
    () => detectGenre(mainArticle.title, mainArticle.extract, wiki.query),
    [mainArticle.title, mainArticle.extract, wiki.query]
  );

  const activeGenre = selectedGenre === 'auto' ? detected : selectedGenre;

  // Filter valid images that haven't errored out
  const validImages = useMemo(() => {
    return wiki.images.filter((img) => !brokenUrls[img.url] && !brokenUrls[img.original_url || '']);
  }, [wiki.images, brokenUrls]);

  const heroImage = validImages[0] || null;
  const galleryImages = validImages.slice(1);

  const dates = useMemo(() => extractEraOrDates(mainArticle.extract), [mainArticle.extract]);
  const location = useMemo(() => extractLocation(mainArticle.extract), [mainArticle.extract]);
  const epithet = useMemo(() => extractEpithet(mainArticle.title, mainArticle.extract), [mainArticle.title, mainArticle.extract]);
  const pullQuote = useMemo(() => extractPullQuote(mainArticle.extract), [mainArticle.extract]);

  // Clean extract paragraphs
  const paragraphs = useMemo(() => {
    const raw = mainArticle.extract.trim();
    const parts = raw.split(/\n\n+/).filter(Boolean);
    if (parts.length > 1) return parts;
    // Split long single paragraph into 2 at a sentence boundary
    const sentences = raw.split(/(?<=[.!?])\s+/);
    if (sentences.length >= 4) {
      const mid = Math.ceil(sentences.length / 2);
      return [sentences.slice(0, mid).join(' '), sentences.slice(mid).join(' ')];
    }
    return [raw];
  }, [mainArticle.extract]);

  const handleImageError = (url: string) => {
    setBrokenUrls((prev) => ({ ...prev, [url]: true }));
  };

  const openLightbox = (index: number) => {
    setActiveLightboxIdx(index);
  };

  const closeLightbox = () => {
    setActiveLightboxIdx(null);
  };

  const nextLightbox = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    if (activeLightboxIdx !== null && validImages.length > 0) {
      setActiveLightboxIdx((activeLightboxIdx + 1) % validImages.length);
    }
  };

  const prevLightbox = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    if (activeLightboxIdx !== null && validImages.length > 0) {
      setActiveLightboxIdx((activeLightboxIdx - 1 + validImages.length) % validImages.length);
    }
  };

  // Keyboard navigation for Lightbox
  useEffect(() => {
    if (activeLightboxIdx === null) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeLightbox();
      if (e.key === 'ArrowRight') nextLightbox();
      if (e.key === 'ArrowLeft') prevLightbox();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeLightboxIdx, validImages.length]);

  return (
    <div className={`wiki-edition-card ${activeGenre}`}>
      {/* Editorial Card Header & Genre Switcher Bar */}
      <div className="wiki-top-bar">
        <div className="wiki-source-tag">
          <span className="wiki-icon-badge">W</span>
          <span className="wiki-rubric">
            {activeGenre === 'biography' && 'Editorial Chronicle · Biography'}
            {activeGenre === 'landmark' && 'Architectural Monograph · Heritage'}
            {activeGenre === 'archival' && 'Museum Archive · Historical Document'}
            {activeGenre === 'folio' && 'Collector Folio · Art & Nature'}
          </span>
        </div>

        {/* Interactive Genre Style Switcher */}
        <div className="wiki-genre-pills" title="Switch knowledge presentation genre">
          <button
            type="button"
            className={`wiki-genre-btn ${selectedGenre === 'auto' ? 'active' : ''}`}
            onClick={() => setSelectedGenre('auto')}
            title="Auto-detect based on article content"
          >
            Auto
          </button>
          <button
            type="button"
            className={`wiki-genre-btn ${activeGenre === 'biography' && selectedGenre !== 'auto' ? 'active' : ''}`}
            onClick={() => setSelectedGenre('biography')}
            title="Hayao Miyazaki / Mark Twain Biography layout"
          >
            Biography
          </button>
          <button
            type="button"
            className={`wiki-genre-btn ${activeGenre === 'landmark' && selectedGenre !== 'auto' ? 'active' : ''}`}
            onClick={() => setSelectedGenre('landmark')}
            title="Taj Mahal Architectural Monument layout"
          >
            Monument
          </button>
          <button
            type="button"
            className={`wiki-genre-btn ${activeGenre === 'archival' && selectedGenre !== 'auto' ? 'active' : ''}`}
            onClick={() => setSelectedGenre('archival')}
            title="US Dollar & Julius Caesar Archival Monograph layout"
          >
            Archival
          </button>
          <button
            type="button"
            className={`wiki-genre-btn ${activeGenre === 'folio' && selectedGenre !== 'auto' ? 'active' : ''}`}
            onClick={() => setSelectedGenre('folio')}
            title="Japanese Woodblock Stamp Card Folio layout"
          >
            Folio
          </button>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* GENRE 1: BIOGRAPHY & CHRONICLE (Hayao Miyazaki & Mark Twain Layout)       */}
      {/* ========================================================================= */}
      {activeGenre === 'biography' && (
        <div className="wiki-genre-body bio-layout">
          <div className="bio-hero-split">
            {/* Left Column: Portrait, Timeline & Quick Stats */}
            <div className="bio-portrait-col">
              {heroImage ? (
                <div
                  className="bio-portrait-frame"
                  onClick={() => openLightbox(0)}
                  title="Click to view high-resolution portrait"
                >
                  <img
                    src={getProxyImageUrl(heroImage.original_url || heroImage.url)}
                    alt={heroImage.title || mainArticle.title}
                    onError={() => handleImageError(heroImage.url)}
                    loading="lazy"
                  />
                  <div className="portrait-zoom-pill">
                    <span>🔍 Full Portrait</span>
                  </div>
                </div>
              ) : (
                <div className="bio-portrait-placeholder">
                  <span>👤</span>
                </div>
              )}

              {/* Lifespan & Timeline Metadata */}
              {dates && (
                <div className="bio-dates-card">
                  <div className="bio-dates-label">Era · Lifespan</div>
                  <div className="bio-dates-value">{dates}</div>
                </div>
              )}
              {location && (
                <div className="bio-meta-sub">
                  <span>📍 {location}</span>
                </div>
              )}
            </div>

            {/* Right Column: Editorial Typography, Flourish, Drop Cap & Narrative */}
            <div className="bio-editorial-col">
              <div className="bio-category-overline">{epithet}</div>
              <h2 className="bio-title-heading">{mainArticle.title}</h2>
              <div className="bio-subtitle-line">
                An authoritative overview of the life, legacy, and work of {mainArticle.title}.
              </div>

              {/* Ornate Flourish Divider (inspired by Miyazaki reference) */}
              <div className="bio-flourish">
                <span className="flourish-char">❧</span>
                <span className="flourish-line"></span>
                <span className="flourish-char">❦</span>
                <span className="flourish-line"></span>
                <span className="flourish-char">❧</span>
              </div>

              {/* Narrative with Drop-Cap */}
              <div className="bio-narrative">
                {paragraphs[0] && (
                  <p className="bio-lead-p">
                    <span className="bio-drop-cap">{paragraphs[0].charAt(0)}</span>
                    {paragraphs[0].slice(1)}
                  </p>
                )}

                {/* Pull Quote Box (inspired by Miyazaki quote callout) */}
                {pullQuote && (
                  <blockquote className="bio-pullquote">
                    <span className="quote-mark">“</span>
                    {pullQuote}
                    <span className="quote-mark">”</span>
                  </blockquote>
                )}

                {paragraphs[1] && (isExpanded || paragraphs.length <= 2) && (
                  <p className="bio-secondary-p">{paragraphs[1]}</p>
                )}

                {paragraphs.length > 2 && !isExpanded && (
                  <button
                    type="button"
                    className="bio-expand-btn"
                    onClick={() => setIsExpanded(true)}
                  >
                    Read complete biography overview ↓
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Curated Works & Archives Horizontal Gallery (inspired by Mark Twain "Books" row) */}
          {galleryImages.length > 0 && (
            <div className="bio-gallery-section">
              <div className="section-header-row">
                <span className="section-title">Notable Works & Historical Archives</span>
                <span className="section-counter">{galleryImages.length} items cataloged</span>
              </div>
              <div className="bio-cards-scroll">
                {galleryImages.map((img, idx) => (
                  <div
                    key={idx}
                    className="bio-work-card"
                    onClick={() => openLightbox(idx + 1)}
                    title={img.caption || img.title}
                  >
                    <div className="bio-work-thumb-wrap">
                      <img
                        src={getProxyImageUrl(img.original_url || img.url)}
                        alt={img.caption || img.title}
                        onError={() => handleImageError(img.url)}
                        loading="lazy"
                      />
                      <span className="bio-card-zoom-badge">Enlarge</span>
                    </div>
                    <div className="bio-work-caption">
                      {img.caption || img.title || `Archive illustration ${idx + 1}`}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* GENRE 2: ARCHITECTURAL MONUMENT & HERITAGE (Taj Mahal Exhibition Layout) */}
      {/* ========================================================================= */}
      {activeGenre === 'landmark' && (
        <div className="wiki-genre-body landmark-layout">
          {/* Panoramic Hero Showcase */}
          {heroImage && (
            <div
              className="landmark-hero-banner"
              onClick={() => openLightbox(0)}
              title="Click to view full panoramic perspective"
            >
              <img
                src={getProxyImageUrl(heroImage.original_url || heroImage.url)}
                alt={heroImage.title || mainArticle.title}
                onError={() => handleImageError(heroImage.url)}
                loading="lazy"
              />
              <div className="landmark-hero-overlay">
                <div className="landmark-hero-tags">
                  <span className="hero-pill">🏛️ Architectural Wonder</span>
                  {dates && <span className="hero-pill">{dates}</span>}
                  {location && <span className="hero-pill">📍 {location}</span>}
                </div>
                <h1 className="landmark-hero-title">{mainArticle.title}</h1>
                <div className="landmark-hero-sub">{epithet}</div>
              </div>
            </div>
          )}

          {/* Monument Narrative Column */}
          <div className="landmark-story-grid">
            <div className="landmark-text-lead">
              {paragraphs[0] && (
                <p>
                  <span className="landmark-drop-cap">{paragraphs[0].charAt(0)}</span>
                  {paragraphs[0].slice(1)}
                </p>
              )}
            </div>
            {paragraphs[1] && (
              <div className="landmark-text-sub">
                <p>{paragraphs[1]}</p>
                {pullQuote && (
                  <div className="landmark-fact-chip">
                    <b>Key Detail:</b> {pullQuote}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Architectural Perspectives & Gallery Grid */}
          {galleryImages.length > 0 && (
            <div className="landmark-perspectives-section">
              <div className="section-header-row">
                <span className="section-title">Architectural Perspectives & Grounds</span>
                <span className="section-counter">{galleryImages.length} views</span>
              </div>
              <div className="landmark-photo-grid">
                {galleryImages.map((img, idx) => (
                  <div
                    key={idx}
                    className="landmark-photo-card"
                    onClick={() => openLightbox(idx + 1)}
                    title={img.caption}
                  >
                    <div className="landmark-img-wrap">
                      <img
                        src={getProxyImageUrl(img.original_url || img.url)}
                        alt={img.caption || img.title}
                        onError={() => handleImageError(img.url)}
                        loading="lazy"
                      />
                    </div>
                    <div className="landmark-photo-label">
                      {img.caption || `Perspective ${idx + 1}`}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* GENRE 3: ARCHIVAL SPECIMEN & MONOGRAPH (US Dollar & Julius Caesar Layout) */}
      {/* ========================================================================= */}
      {activeGenre === 'archival' && (
        <div className="wiki-genre-body archival-layout">
          <div className="archival-container">
            <div className="archival-header-strip">
              <span className="archive-cat">DOC. ARCHIVE SPECIMEN</span>
              <span className="archive-stamp">REF-ENWIKI-{mainArticle.title.slice(0, 4).toUpperCase()}</span>
            </div>

            <div className="archival-main-split">
              {/* Left Column: Hero Specimen Artifact */}
              {heroImage && (
                <div className="archival-specimen-col">
                  <div
                    className="archival-specimen-frame"
                    onClick={() => openLightbox(0)}
                    title="Click to inspect specimen at high magnification"
                  >
                    <img
                      src={getProxyImageUrl(heroImage.original_url || heroImage.url)}
                      alt={heroImage.title || mainArticle.title}
                      onError={() => handleImageError(heroImage.url)}
                      loading="lazy"
                    />
                    <div className="specimen-tag">
                      <span>FIG. 01 — {heroImage.caption ? heroImage.caption.slice(0, 32) : 'PRIMARY SPECIMEN'}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Right Column: Monograph Narrative & Key Term Highlights */}
              <div className="archival-monograph-col">
                <h1 className="archival-title">{mainArticle.title}</h1>
                <div className="archival-epithet">{epithet}</div>
                {dates && <div className="archival-era">ERA / CHRONOLOGY: {dates}</div>}

                <div className="archival-prose">
                  {paragraphs.map((p, pIdx) => (
                    <p key={pIdx} className={pIdx === 0 ? 'lead-prose' : ''}>
                      {pIdx === 0 && <span className="archival-drop-cap">{p.charAt(0)}</span>}
                      {/* Highlight prominent historical terms */}
                      {pIdx === 0
                        ? p.slice(1).replace(/(treaty|currency|war|dollar|empire|congress|senate|republic)/gi, (m) => `[[HL]]${m}[[HL]]`)
                            .split('[[HL]]')
                            .map((chunk, cIdx) =>
                              cIdx % 2 === 1 ? (
                                <mark key={cIdx} className="wiki-highlight">
                                  {chunk}
                                </mark>
                              ) : (
                                chunk
                              )
                            )
                        : p}
                    </p>
                  ))}
                </div>
              </div>
            </div>

            {/* Inset Secondary Artifacts Strip */}
            {galleryImages.length > 0 && (
              <div className="archival-secondary-strip">
                <div className="archival-sub-title">Cataloged Artifacts & Comparative Plates</div>
                <div className="archival-plates-row">
                  {galleryImages.map((img, idx) => (
                    <div
                      key={idx}
                      className="archival-plate-card"
                      onClick={() => openLightbox(idx + 1)}
                      title={img.caption}
                    >
                      <div className="archival-plate-thumb">
                        <img
                          src={getProxyImageUrl(img.original_url || img.url)}
                          alt={img.caption || img.title}
                          onError={() => handleImageError(img.url)}
                          loading="lazy"
                        />
                      </div>
                      <div className="archival-plate-desc">
                        <b>PLATE 0{idx + 2}</b> · {img.caption || img.title}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* GENRE 4: COLLECTOR STAMP FOLIO (Japanese Woodblock Stamp Cards Layout)    */}
      {/* ========================================================================= */}
      {activeGenre === 'folio' && (
        <div className="wiki-genre-body folio-layout">
          <div className="folio-intro">
            <h2 className="folio-headline">{mainArticle.title}</h2>
            <p className="folio-subhead">{mainArticle.extract.slice(0, 240)}…</p>
          </div>

          <div className="folio-stamps-grid">
            {validImages.map((img, idx) => (
              <div
                key={idx}
                className="folio-stamp-card"
                onClick={() => openLightbox(idx)}
                title="Click to view stamp print in high definition"
              >
                {/* Stamp Perforated Header */}
                <div className="stamp-header">
                  <div className="stamp-emblem">✦</div>
                  <div className="stamp-number">0{idx + 1}</div>
                </div>

                <div className="stamp-body-text">
                  <div className="stamp-topic">
                    {idx === 0
                      ? mainArticle.title
                      : img.caption
                      ? img.caption.slice(0, 48)
                      : `Collection Plate 0${idx + 1}`}
                  </div>
                  <div className="stamp-desc">
                    {img.caption || 'Archival photographic print cataloged in Wikipedia library.'}
                  </div>
                </div>

                {/* Stamp Artwork Artwork Plate */}
                <div className="stamp-image-plate">
                  <img
                    src={getProxyImageUrl(img.original_url || img.url)}
                    alt={img.caption || img.title}
                    onError={() => handleImageError(img.url)}
                    loading="lazy"
                  />
                  <div className="stamp-scallop-edge"></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Card Footer: Direct Wikipedia Link & Companion Badge */}
      <div className="wiki-card-footer">
        <a
          href={mainArticle.url}
          target="_blank"
          rel="noopener noreferrer"
          className="wiki-read-external-btn"
        >
          <span>Read complete article on Wikipedia</span>
          <span className="wiki-external-arrow">↗</span>
        </a>

        <div className="wiki-curator-note">
          <span>Curated with local AI · {companion === 'ember' ? '🔥 Ember' : '🤖 Frost'}</span>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* HIGH RESOLUTION LIGHTBOX MODAL (Image Inspection at Full Magnification)   */}
      {/* ========================================================================= */}
      {activeLightboxIdx !== null && validImages[activeLightboxIdx] && (
        <div className="wiki-lightbox-backdrop" onClick={closeLightbox}>
          <div className="wiki-lightbox-modal" onClick={(e) => e.stopPropagation()}>
            {/* Top Navigation & Close */}
            <div className="lightbox-top-bar">
              <div className="lightbox-counter">
                Plate <b>{activeLightboxIdx + 1}</b> of {validImages.length}
              </div>
              <div className="lightbox-title-bar">
                {validImages[activeLightboxIdx].title || mainArticle.title}
              </div>
              <button
                type="button"
                className="lightbox-close-btn"
                onClick={closeLightbox}
                title="Close Lightbox (Esc)"
              >
                ✕
              </button>
            </div>

            {/* Main Stage with Prev / Next Buttons */}
            <div className="lightbox-stage">
              {validImages.length > 1 && (
                <button
                  type="button"
                  className="lightbox-nav-arrow left"
                  onClick={prevLightbox}
                  title="Previous image (←)"
                >
                  ‹
                </button>
              )}

              <div className="lightbox-image-container">
                <img
                  src={getProxyImageUrl(
                    validImages[activeLightboxIdx].original_url || validImages[activeLightboxIdx].url
                  )}
                  alt={validImages[activeLightboxIdx].caption || 'Wikipedia Inspection'}
                  loading="eager"
                />
              </div>

              {validImages.length > 1 && (
                <button
                  type="button"
                  className="lightbox-nav-arrow right"
                  onClick={nextLightbox}
                  title="Next image (→)"
                >
                  ›
                </button>
              )}
            </div>

            {/* Bottom Caption & Link */}
            <div className="lightbox-caption-bar">
              <div className="lightbox-caption-text">
                {validImages[activeLightboxIdx].caption ||
                  validImages[activeLightboxIdx].title ||
                  'High resolution archival photograph from Wikimedia Commons.'}
              </div>
              {mainArticle.url && (
                <a
                  href={mainArticle.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="lightbox-wiki-link"
                >
                  Open in Wikipedia ↗
                </a>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default WikiKnowledgeCard;
