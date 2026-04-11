# Requirements Document: Codefolio

## Introduction

Codefolio is a GitHub profile analyzer that transforms developer contribution data into professional resumes and shareable social cards. The system fetches GitHub data via GraphQL API, calculates a multi-dimensional developer score (GitScore), generates AI-powered insights, and produces both Markdown/PDF resumes and PNG social cards for sharing.

## Glossary

- **System**: The Codefolio application (frontend + backend)
- **GitHub_API**: GitHub's GraphQL API v4
- **GitScore**: A 0-100 score calculated from 5 dimensions of developer activity
- **Social_Card**: A PNG image containing developer stats, tags, and visual elements
- **Resume**: A Markdown or PDF document summarizing developer profile
- **Cache_Layer**: Redis-based caching system for API responses and AI results
- **AI_Service**: LLM integration for generating summaries, tags, and comments
- **Score_Engine**: Algorithm that calculates GitScore from GitHub data
- **Render_Service**: Component that generates Markdown, HTML, and PNG outputs

## Requirements

### Requirement 1: GitHub Data Fetching

**User Story:** As a user, I want to input my GitHub username and have the system fetch my profile data, so that I can generate my developer resume and social card.

#### Acceptance Criteria

1. WHEN a user provides a valid GitHub username, THE System SHALL fetch user profile data via GitHub_API GraphQL endpoint
2. WHEN fetching GitHub data, THE System SHALL retrieve user information, repository list, contribution statistics, and language distribution in a single request
3. WHEN GitHub_API returns data, THE System SHALL normalize it into a standardized JSON format
4. IF GitHub_API rate limit is exceeded, THEN THE System SHALL return an error message indicating rate limit status
5. IF a GitHub username does not exist, THEN THE System SHALL return a user-friendly error message
6. WHEN GitHub data is successfully fetched, THE System SHALL store the response in Cache_Layer with 24-hour TTL

### Requirement 2: GitScore Calculation Engine

**User Story:** As a user, I want to see a quantified score of my developer capabilities, so that I can understand my strengths and share my achievements.

#### Acceptance Criteria

1. WHEN GitHub data is available, THE Score_Engine SHALL calculate a GitScore between 0 and 100
2. THE Score_Engine SHALL calculate project impact score (0-35 points) based on total stars and forks across repositories
3. THE Score_Engine SHALL calculate code contribution score (0-25 points) based on commits and pull requests in the last year
4. THE Score_Engine SHALL calculate community activity score (0-20 points) based on followers and following counts
5. THE Score_Engine SHALL calculate tech breadth score (0-15 points) based on number of distinct programming languages used
6. THE Score_Engine SHALL calculate documentation score (0-5 points) based on presence of README and LICENSE files
7. WHEN calculating dimension scores, THE Score_Engine SHALL apply normalization to prevent single outlier values from dominating the score
8. THE System SHALL return both the total GitScore and individual dimension scores

### Requirement 3: AI-Powered Feature Generation

**User Story:** As a user, I want AI-generated insights about my coding style, so that I can share interesting and engaging content on social media.

#### Acceptance Criteria

1. WHEN GitHub data is processed, THE AI_Service SHALL generate 3-5 style tags describing the developer's coding patterns
2. WHEN generating style tags, THE AI_Service SHALL use structured prompts to ensure tags are 2-4 characters in Chinese or English
3. WHEN GitHub data is processed, THE AI_Service SHALL generate a single roast comment (maximum 30 characters) that is humorous but respectful
4. WHEN generating roast comments, THE AI_Service SHALL avoid personal attacks and use programming-related humor
5. WHEN GitHub data is processed, THE AI_Service SHALL generate a tech stack summary highlighting the developer's primary technologies
6. WHEN AI_Service generates content, THE System SHALL cache results in Cache_Layer to reduce API costs
7. IF AI_Service fails or times out, THEN THE System SHALL use fallback generic tags and skip the roast comment

### Requirement 4: Resume Generation

**User Story:** As a job seeker, I want to generate a professional resume from my GitHub data, so that I can present my technical skills to potential employers.

#### Acceptance Criteria

1. WHEN all data is collected, THE Render_Service SHALL generate a Markdown resume containing user profile, GitScore breakdown, top repositories, and tech stack distribution
2. THE Render_Service SHALL format the resume using a professional template with clear sections and hierarchy
3. WHEN a user requests PDF export, THE System SHALL convert the Markdown resume to PDF format
4. THE System SHALL include contribution heatmap data in the resume
5. THE System SHALL list top repositories sorted by stars with descriptions
6. THE System SHALL include language distribution as percentages
7. WHEN generating resume, THE System SHALL include AI-generated tech stack summary if available

### Requirement 5: Social Card Rendering

**User Story:** As a developer, I want to generate a visually appealing social card, so that I can share my developer profile on social media platforms.

#### Acceptance Criteria

1. WHEN resume generation is complete, THE Render_Service SHALL generate a PNG social card image
2. THE Social_Card SHALL include user avatar, username, GitScore with visual indicator, style tags, and roast comment
3. THE Social_Card SHALL include tech stack icons for the developer's primary languages
4. THE Social_Card SHALL use an attractive background design with proper contrast for readability
5. THE Social_Card SHALL be sized appropriately for social media sharing (recommended 1200x630 pixels)
6. WHEN rendering the social card, THE System SHALL support both frontend rendering (html2canvas) and backend rendering (playwright)
7. THE System SHALL allow users to download the generated social card as PNG

### Requirement 6: Caching Layer

**User Story:** As a system operator, I want to cache API responses and AI results, so that I can reduce costs and improve response times.

#### Acceptance Criteria

1. WHEN GitHub_API data is fetched, THE Cache_Layer SHALL store the response with a 24-hour TTL
2. WHEN a user requests data for a username, THE System SHALL check Cache_Layer before calling GitHub_API
3. IF cached data exists and is not expired, THEN THE System SHALL return cached data without calling GitHub_API
4. WHEN AI_Service generates content, THE Cache_Layer SHALL store results with username as key
5. THE Cache_Layer SHALL use Redis as the caching backend
6. WHEN cache storage fails, THE System SHALL log the error and continue without caching

### Requirement 7: Frontend User Interface

**User Story:** As a user, I want an intuitive web interface, so that I can easily generate and view my developer profile.

#### Acceptance Criteria

1. WHEN a user visits the application, THE System SHALL display an input page with a prominent GitHub username field
2. THE System SHALL provide example usernames for quick testing
3. WHEN a user submits a username, THE System SHALL display a loading state with progress indicators or engaging messages
4. WHEN generation is complete, THE System SHALL display a results page with GitScore visualization, resume preview, and social card
5. THE System SHALL provide action buttons for downloading PNG, copying resume, and regenerating
6. THE System SHALL display a radar chart visualizing the five GitScore dimensions
7. WHEN displaying results, THE System SHALL allow users to preview the resume in Markdown format with copy functionality

### Requirement 8: API Backend

**User Story:** As a frontend developer, I want a RESTful API, so that I can integrate the backend services with the user interface.

#### Acceptance Criteria

1. THE System SHALL provide a POST endpoint `/api/generate` accepting a GitHub username
2. WHEN `/api/generate` is called, THE System SHALL return a JSON response containing resume data, GitScore, style tags, roast comment, and social card data
3. THE System SHALL provide a GET endpoint `/api/export/pdf` for PDF resume generation
4. THE System SHALL implement proper error handling with appropriate HTTP status codes
5. THE System SHALL implement rate limiting to prevent abuse
6. THE System SHALL return CORS headers to allow frontend access
7. WHEN API errors occur, THE System SHALL return structured error responses with error codes and messages

### Requirement 9: Data Privacy and Security

**User Story:** As a user, I want my data to be handled securely, so that I can trust the application with my GitHub information.

#### Acceptance Criteria

1. THE System SHALL only access public GitHub data and SHALL NOT request private repository access
2. THE System SHALL NOT store user passwords or authentication tokens permanently
3. WHEN storing cached data, THE System SHALL only cache public information
4. THE System SHALL implement HTTPS for all API communications
5. THE System SHALL sanitize user inputs to prevent injection attacks
6. THE System SHALL comply with GitHub API terms of service

### Requirement 10: Performance and Scalability

**User Story:** As a system operator, I want the application to perform efficiently, so that users have a smooth experience even under load.

#### Acceptance Criteria

1. WHEN processing a request, THE System SHALL complete the entire generation workflow within 10 seconds under normal conditions
2. THE System SHALL handle at least 100 concurrent requests without degradation
3. WHEN GitHub_API is slow, THE System SHALL implement timeout handling (maximum 30 seconds)
4. THE System SHALL use asynchronous processing for I/O operations
5. WHEN AI_Service calls are made, THE System SHALL implement timeout handling (maximum 15 seconds)
6. THE System SHALL log performance metrics for monitoring and optimization

### Requirement 11: Internationalization (i18n)

**User Story:** As a user, I want to switch between Chinese and English languages, so that I can use the application in my preferred language.

#### Acceptance Criteria

1. THE System SHALL support Chinese (Simplified) and English language options
2. WHEN a user selects a language, THE System SHALL persist the language preference in browser localStorage
3. THE System SHALL display a language toggle button in the header navigation
4. WHEN language is changed, THE System SHALL update all UI text, labels, buttons, and messages without page reload
5. THE System SHALL translate AI-generated content (style tags, roast comments) based on selected language
6. THE System SHALL default to browser language if available, otherwise default to English
7. WHEN generating resume, THE System SHALL use the selected language for section headers and labels
8. THE System SHALL maintain language consistency across all pages (input, loading, results)

### Requirement 12: Theme Switching (Light/Dark Mode)

**User Story:** As a user, I want to switch between light and dark themes, so that I can use the application comfortably in different lighting conditions.

#### Acceptance Criteria

1. THE System SHALL support both light mode and dark mode themes
2. WHEN a user selects a theme, THE System SHALL persist the theme preference in browser localStorage
3. THE System SHALL display a theme toggle button in the header navigation
4. WHEN theme is changed, THE System SHALL update all colors, backgrounds, and UI elements smoothly with CSS transitions
5. THE System SHALL default to system preference (prefers-color-scheme) if no user preference is stored
6. THE System SHALL ensure text contrast meets WCAG 2.1 AA standards (4.5:1 minimum) in both themes
7. WHEN in light mode, THE System SHALL use light backgrounds with dark text and appropriate color adjustments
8. WHEN in dark mode, THE System SHALL use dark backgrounds with light text following the existing color palette
9. THE System SHALL apply theme consistently to all components including social cards, charts, and modals
10. THE System SHALL respect prefers-reduced-motion for theme transition animations
