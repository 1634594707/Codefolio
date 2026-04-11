# Implementation Plan: Codefolio

## Overview

This implementation plan breaks down the Codefolio feature into discrete coding tasks. The approach follows a bottom-up strategy: build core services first (GitHub data fetching, scoring, AI generation), then add rendering capabilities, followed by API layer, and finally the frontend UI. Each task builds incrementally to ensure continuous integration and early validation.

## Product Improvement Roadmap

- [ ] Phase A - Usability and trust baseline
  - [ ] A.1 Fix all Chinese text encoding issues across frontend, backend templates, and docs
  - [x] A.2 Separate interface language from generated content language
  - [x] A.3 Reduce first-run latency by generating only the actively selected content language
  - [ ] A.4 Upgrade loading states with clearer progress feedback
  - [ ] A.5 Replace the lightweight text-only PDF path with a styled export path that supports Chinese

- [ ] Phase B - Better result quality
  - [ ] B.1 Add GitScore explanations for each dimension
  - [ ] B.2 Add actionable suggestions for improving GitScore
  - [ ] B.3 Improve project ranking beyond stars-only ordering
  - [ ] B.4 Add multiple AI output modes: job-seeking, social sharing, recruiter snapshot
  - [ ] B.5 Make roast comments optional or tone-selectable

- [ ] Phase C - Editing and export workflow
  - [ ] C.1 Add editable summary, tags, and featured project ordering
  - [ ] C.2 Allow hiding repos from generated outputs
  - [ ] C.3 Add resume/card template variants
  - [ ] C.4 Add shareable public result links in addition to file download

- [ ] Phase D - Retention features
  - [ ] D.1 Save generation history and profile snapshots
  - [ ] D.2 Add score and profile comparison across snapshots
  - [ ] D.3 Add personalized growth suggestions based on current profile data
  - [ ] D.4 Add scenario-specific output presets for student, full-stack, open-source, indie hacker

- [ ] Phase E - Engineering quality
  - [ ] E.1 Repair backend test execution and align async test tooling
  - [ ] E.2 Add integration coverage for generation, export, and language switching
  - [ ] E.3 Reduce frontend bundle size and split heavy client-only features
  - [ ] E.4 Consolidate duplicated rendering and translation responsibilities
  - [ ] E.5 Add performance instrumentation for GitHub, AI, cache, and export stages

## Tasks

- [x] 1. Project setup and infrastructure
  - Initialize Python backend with FastAPI, configure project structure with services directory
  - Initialize React frontend with Vite and Tailwind CSS
  - Set up Redis connection and caching utilities
  - Configure environment variables for GitHub token, AI API keys, Redis URL
  - _Requirements: 8.6, 6.5_

- [x] 2. Implement GitHub data fetching service
  - [x] 2.1 Create GitHubService class with GraphQL query builder
    - Implement `fetch_user_data()` method with comprehensive GraphQL query
    - Add user profile, repositories, contributions, and language data fetching
    - Implement data normalization to UserData model
    - _Requirements: 1.1, 1.2, 1.3_
  
  - [x] 2.2 Add error handling and rate limiting
    - Implement GitHub API rate limit checking with `check_rate_limit()`
    - Add error handling for non-existent users and API failures
    - Return structured error responses with appropriate messages
    - _Requirements: 1.4, 1.5_
  
  - [x] 2.3 Integrate Redis caching for GitHub responses
    - Check cache before API calls with 24-hour TTL
    - Store normalized responses in Redis with `github:user:{username}` key pattern
    - Handle cache failures gracefully with logging
    - _Requirements: 1.6, 6.1, 6.2, 6.3, 6.6_
  
  - [ ]* 2.4 Write property test for GitHub data fetching
    - **Property 1: Cache hit consistency**
    - **Validates: Requirements 6.2, 6.3**
  
  - [ ]* 2.5 Write unit tests for error scenarios
    - Test non-existent username handling
    - Test rate limit exceeded scenario
    - Test cache failure fallback
    - _Requirements: 1.4, 1.5, 6.6_

- [x] 3. Implement GitScore calculation engine
  - [x] 3.1 Create ScoreEngine class with dimension calculators
    - Implement `calculate_gitscore()` main method
    - Implement `_calculate_impact_score()` using stars and forks formula
    - Implement `_calculate_contribution_score()` using commits and PRs
    - Implement `_calculate_community_score()` using followers/following
    - Implement `_calculate_tech_breadth_score()` using language diversity
    - Implement `_calculate_documentation_score()` using README/LICENSE presence
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.8_
  
  - [x] 3.2 Add normalization to prevent outlier domination
    - Apply min() capping to each dimension score
    - Ensure total score stays within 0-100 range
    - _Requirements: 2.7_
  
  - [ ]* 3.3 Write property test for score calculation
    - **Property 2: Score bounds invariant**
    - **Validates: Requirements 2.1, 2.7**
  
  - [ ]* 3.4 Write property test for dimension scoring
    - **Property 3: Dimension sum consistency**
    - **Validates: Requirements 2.2, 2.3, 2.4, 2.5, 2.6**
  
  - [ ]* 3.5 Write unit tests for edge cases
    - Test empty repository list
    - Test zero contributions
    - Test single language developer
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 4. Checkpoint - Ensure core services work
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement AI service for insights generation
  - [x] 5.1 Create AIService class with LLM integration
    - Set up async HTTP client for AI API calls
    - Implement `generate_style_tags()` with structured prompt
    - Implement `generate_roast_comment()` with humor guidelines
    - Implement `generate_tech_summary()` for tech stack description
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  
  - [x] 5.2 Add caching for AI-generated content
    - Cache style tags, roast comments, and summaries separately
    - Use 7-day TTL for AI results
    - Implement cache key pattern: `ai:{username}:{content_type}`
    - _Requirements: 3.6_
  
  - [x] 5.3 Implement fallback handling for AI failures
    - Return generic tags when AI service times out
    - Skip roast comment on failure
    - Add timeout handling (15 seconds max)
    - _Requirements: 3.7, 10.5_
  
  - [ ]* 5.4 Write unit tests for AI service
    - Test prompt formatting
    - Test timeout handling
    - Test fallback behavior
    - _Requirements: 3.7, 10.5_

- [ ] 6. Implement render service for output generation
  - [ ] 6.1 Create RenderService class with Markdown generator
    - Implement `generate_markdown_resume()` using template structure
    - Include GitScore breakdown, top repositories, tech stack, AI insights
    - Format contribution stats and language distribution
    - _Requirements: 4.1, 4.2, 4.4, 4.5, 4.6, 4.7_
  
  - [ ] 6.2 Add PDF export functionality
    - Implement `generate_pdf_resume()` using WeasyPrint or ReportLab
    - Convert Markdown to styled PDF with proper formatting
    - _Requirements: 4.3_
  
  - [ ] 6.3 Implement social card PNG generation
    - Create HTML template for social card layout (1200x630)
    - Include avatar, username, GitScore, radar chart, style tags, roast comment
    - Add tech stack icons for primary languages
    - Implement attractive background with proper contrast
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
  
  - [ ] 6.4 Add server-side rendering with Playwright
    - Set up Playwright for headless browser rendering
    - Implement `generate_social_card()` to render HTML to PNG
    - Support both frontend (html2canvas) and backend rendering paths
    - _Requirements: 5.6, 5.7_
  
  - [ ]* 6.5 Write property test for resume generation
    - **Property 4: Resume completeness**
    - **Validates: Requirements 4.1, 4.4, 4.5, 4.6**
  
  - [ ]* 6.6 Write unit tests for rendering edge cases
    - Test missing AI insights
    - Test empty repository list
    - Test long usernames and bios
    - _Requirements: 4.1, 5.1_

- [ ] 7. Checkpoint - Ensure rendering pipeline works
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Implement FastAPI backend endpoints
  - [ ] 8.1 Create API router with main endpoints
    - Implement POST `/api/generate` endpoint
    - Implement GET `/api/export/pdf` endpoint
    - Implement GET `/api/health` health check endpoint
    - _Requirements: 8.1, 8.2, 8.3_
  
  - [ ] 8.2 Wire services together in generation workflow
    - Orchestrate: GitHub fetch → Score calculation → AI generation → Rendering
    - Return JSON response with resume, GitScore, AI insights, card data
    - Handle async operations properly
    - _Requirements: 8.2, 10.4_
  
  - [ ] 8.3 Add comprehensive error handling
    - Implement HTTP status codes (400, 404, 429, 500, 503)
    - Return structured error responses with codes and messages
    - Add timeout handling for external services
    - _Requirements: 8.4, 10.3_
  
  - [ ] 8.4 Implement rate limiting and CORS
    - Add rate limiting middleware to prevent abuse
    - Configure CORS headers for frontend access
    - _Requirements: 8.5, 8.6_
  
  - [ ] 8.5 Add input sanitization for security
    - Validate and sanitize GitHub username input
    - Prevent injection attacks
    - _Requirements: 9.5_
  
  - [ ]* 8.6 Write integration tests for API endpoints
    - Test complete generation workflow
    - Test error scenarios (invalid username, rate limits)
    - Test PDF export endpoint
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [ ] 9. Implement React frontend UI
  - [ ] 9.1 Create input page component
    - Build GitHub username input field with validation
    - Add example usernames for quick testing
    - Style with Tailwind CSS following professional design patterns
    - _Requirements: 7.1, 7.2_
  
  - [x] 9.2 Create loading state component
    - Display progress indicators or engaging messages
    - Show loading animation during API call
    - _Requirements: 7.3_
  
  - [ ] 9.3 Create results page component
    - Display GitScore with visual indicator
    - Show radar chart for five dimensions using Recharts
    - Display resume preview with Markdown formatting
    - Show social card preview
    - _Requirements: 7.4, 7.6, 7.7_
  
  - [ ] 9.4 Add action buttons and download functionality
    - Implement PNG download button for social card
    - Implement copy-to-clipboard for resume Markdown
    - Add regenerate button to fetch fresh data
    - _Requirements: 7.5_
  
  - [ ] 9.5 Integrate with backend API
    - Set up Axios for API communication
    - Call POST `/api/generate` on username submission
    - Handle API errors and display user-friendly messages
    - _Requirements: 8.1, 8.2_
  
  - [ ] 9.6 Add client-side social card rendering
    - Implement html2canvas for PNG generation in browser
    - Provide fallback to backend rendering if needed
    - _Requirements: 5.6, 5.7_
  
  - [ ]* 9.7 Write unit tests for React components
    - Test input validation
    - Test loading state transitions
    - Test results display
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [ ] 10. Implement data privacy and security measures
  - [ ] 10.1 Ensure public data access only
    - Verify GitHub GraphQL query only accesses public data
    - Do not request private repository access
    - _Requirements: 9.1_
  
  - [ ] 10.2 Configure HTTPS and secure storage
    - Ensure all API communications use HTTPS
    - Only cache public information in Redis
    - Do not store passwords or auth tokens permanently
    - _Requirements: 9.2, 9.3, 9.4_
  
  - [ ] 10.3 Verify GitHub API terms compliance
    - Review and comply with GitHub API terms of service
    - Add attribution if required
    - _Requirements: 9.6_

- [ ] 11. Add performance monitoring and optimization
  - [ ] 11.1 Implement performance logging
    - Log execution time for each service call
    - Track GitHub API response times
    - Monitor AI service latency
    - _Requirements: 10.6_
  
  - [ ] 11.2 Optimize for target performance metrics
    - Ensure complete workflow finishes within 10 seconds
    - Verify async operations are properly implemented
    - Test with concurrent requests (target: 100 concurrent)
    - _Requirements: 10.1, 10.2, 10.4_
  
  - [ ]* 11.3 Write performance tests
    - Test workflow completion time
    - Test concurrent request handling
    - Test timeout scenarios
    - _Requirements: 10.1, 10.2, 10.3, 10.5_

- [ ] 12. Implement internationalization (i18n) system
  - [ ] 12.1 Create translation files for English and Chinese
    - Create JSON translation files with all UI text, labels, buttons, messages
    - Include translations for navigation, hero section, GitScore labels, buttons, error messages
    - Organize translations by component/section (nav, hero, gitscore, resume, etc.)
    - _Requirements: 11.1, 11.8_
  
  - [ ] 12.2 Implement I18nService for backend
    - Create I18nService class with language initialization
    - Implement `translate()` method for key-based lookups
    - Implement `format_number()` for locale-specific number formatting
    - Implement `get_ai_prompt_language()` to instruct AI on output language
    - _Requirements: 11.5, 11.7_
  
  - [ ] 12.3 Create LanguageManager for frontend
    - Implement LanguageManager class with localStorage persistence
    - Implement `getInitialLanguage()` to check localStorage then browser language
    - Implement `setLanguage()` to update language and persist preference
    - Implement `translate()` method for key-based translations
    - Implement `updateUI()` to refresh all elements with data-i18n attributes
    - _Requirements: 11.2, 11.6, 11.8_
  
  - [ ] 12.4 Create LanguageToggle React component
    - Build toggle button component with EN/中文 labels
    - Integrate with LanguageManager to switch languages
    - Add to header navigation
    - Trigger UI update on language change without page reload
    - _Requirements: 11.3, 11.4_
  
  - [ ] 12.5 Update API to support language parameter
    - Modify GenerateRequest to accept language parameter ("en" or "zh")
    - Pass language to I18nService for resume generation
    - Pass language instruction to AI service for translated content
    - _Requirements: 11.5, 11.7_
  
  - [ ] 12.6 Update all React components with i18n support
    - Replace hardcoded text with translation keys using data-i18n attributes
    - Update input page, loading page, results page with translations
    - Ensure language consistency across all pages
    - _Requirements: 11.4, 11.8_
  
  - [ ]* 12.7 Write property test for i18n completeness
    - **Property 5: Translation key coverage**
    - **Validates: Requirements 11.1, 11.8**
  
  - [ ]* 12.8 Write unit tests for language switching
    - Test localStorage persistence
    - Test browser language detection
    - Test UI update without page reload
    - _Requirements: 11.2, 11.4, 11.6_

- [ ] 13. Implement theme switching system
  - [ ] 13.1 Define CSS variables for light and dark themes
    - Create CSS variable definitions in root and .dark class
    - Define light mode colors (primary, secondary, tertiary, backgrounds, text, outlines)
    - Define dark mode colors using existing palette
    - Add smooth transitions for color changes (200ms ease)
    - Add prefers-reduced-motion media query to disable transitions
    - _Requirements: 12.1, 12.4, 12.7, 12.8, 12.10_
  
  - [ ] 13.2 Create ThemeManager for frontend
    - Implement ThemeManager class with localStorage persistence
    - Implement `getInitialTheme()` to check localStorage then system preference
    - Implement `toggleTheme()` to switch themes and persist preference
    - Implement `applyTheme()` to add/remove dark class on document root
    - _Requirements: 12.2, 12.5_
  
  - [ ] 13.3 Create ThemeToggle React component
    - Build toggle button component with sun/moon icons
    - Integrate with ThemeManager to switch themes
    - Add to header navigation
    - Trigger smooth theme transition on toggle
    - _Requirements: 12.3, 12.4_
  
  - [ ] 13.4 Update all components to use CSS variables
    - Replace hardcoded colors with CSS variable references
    - Update backgrounds, text colors, borders, shadows to use theme variables
    - Ensure all components (cards, buttons, inputs, charts) support both themes
    - _Requirements: 12.9_
  
  - [ ] 13.5 Verify WCAG contrast requirements
    - Test text contrast ratios in both light and dark modes
    - Ensure minimum 4.5:1 contrast for normal text
    - Adjust colors if needed to meet WCAG 2.1 AA standards
    - _Requirements: 12.6_
  
  - [ ] 13.6 Update social card rendering for theme support
    - Modify social card template to respect current theme
    - Ensure social cards render correctly in both light and dark modes
    - Update Playwright rendering to support theme parameter
    - _Requirements: 12.9_
  
  - [ ]* 13.7 Write property test for theme consistency
    - **Property 6: Theme variable completeness**
    - **Validates: Requirements 12.1, 12.9**
  
  - [ ]* 13.8 Write unit tests for theme switching
    - Test localStorage persistence
    - Test system preference detection
    - Test smooth transitions
    - Test prefers-reduced-motion handling
    - _Requirements: 12.2, 12.4, 12.5, 12.10_

- [ ] 14. Final checkpoint - End-to-end validation with i18n and theme
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- The implementation follows a bottom-up approach: services → API → frontend
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties across all inputs
- Unit tests validate specific examples, edge cases, and error conditions
- Frontend uses React + Tailwind CSS, backend uses Python + FastAPI as specified in design
- Redis caching is critical for reducing API costs and improving performance
