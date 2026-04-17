# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - UI Guidelines Violations Across Page Components
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bugs exist
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fixes when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the violations exist
  - **Scoped PBT Approach**: For each page component, render with arbitrary valid props and assert the accessibility/HTML correctness properties
  - Create `frontend/src/pages/UIGuidelinesCompliance.test.tsx` using `fast-check` (already in devDependencies)
  - For each page component (CompareRepos, Compare, Repositories, Export, AIAnalysis, Overview), render with arbitrary valid props and assert:
    - No `<img>` element is rendered without both `width` and `height` attributes (from Bug Condition 1.13‚Ä?.17)
    - No `<button>` element is rendered without a `type` attribute (from Bug Condition 1.27‚Ä?.29)
    - No element with an `onClick` handler is a `<div>` or `<span>` ‚Ä?must be `<button>` or `<a>` (from Bug Condition 1.9)
    - No `<input>` of type text/search is rendered without `aria-label` or an associated `<label>` (from Bug Condition 1.20)
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the violations exist)
  - Document counterexamples found (e.g., `<img src="..." alt="...">` missing width/height, `<button onClick={...}>` missing type, `<div onClick={...}>` in Overview history items, search input missing aria-label in Repositories)
  - Mark task complete when test is written, run, and failures are documented
  - _Requirements: 1.9, 1.13, 1.14, 1.15, 1.16, 1.17, 1.20, 1.27, 1.28, 1.29_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Functional Behavior Unchanged After Attribute Corrections
  - **IMPORTANT**: Follow observation-first methodology
  - Observe: form inputs accept input and trigger state updates on unfixed code
  - Observe: buttons execute their onClick handlers on unfixed code
  - Observe: repository card link opens URL in new tab on unfixed code
  - Observe: history item click navigates to AI Analysis page on unfixed code
  - Observe: loading states display correct translated text on unfixed code
  - Observe: avatars render at the same visual size defined by CSS classes on unfixed code
  - Write property-based tests capturing observed behavior patterns from Preservation Requirements:
    - For all valid username inputs, the Compare username input updates state and triggers addUser on Enter (from Preservation Requirement 3.1)
    - For all corrected buttons, the onClick handler fires with the same arguments (from Preservation Requirement 3.2)
    - For Repositories cards after restructure, the repo link area and action buttons remain independently clickable (from Preservation Requirement 3.3)
    - For Overview history items after div‚Üíbutton change, activation navigates to AI Analysis (from Preservation Requirement 3.4)
    - For all loading states, the translated text content is preserved ‚Ä?only the ellipsis character changes (from Preservation Requirement 3.5)
  - Verify tests pass on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10_

- [x] 3. Fix CompareRepos.tsx ‚Ä?ellipsis, input attributes, checkbox label, aria-live, role="alert"

  - [x] 3.1 Replace ASCII `...` with Unicode `‚Ä¶` in all loading/async copy strings (en + zh labels)
    - In `labels.en`: change `'Benchmarking...'` ‚Ü?`'Benchmarking‚Ä?`, `'Finding suggestions...'` ‚Ü?`'Finding suggestions‚Ä?`
    - In `labels.zh`: change `'ÂØπÊ†á‰∏?..'` ‚Ü?`'ÂØπÊ†á‰∏≠‚Ä?`, `'Ê≠£Âú®Êü•ÊâæÊé®Ëçê...'` ‚Ü?`'Ê≠£Âú®Êü•ÊâæÊé®Ëçê‚Ä?`
    - Also update any other `...` occurrences in label strings (e.g. `'Âä†ËΩΩ‰∏?..'` if present)
    - _Bug_Condition: isBugCondition(labels) where labels contain ASCII `...` in loading/async copy_
    - _Expected_Behavior: All loading/async copy uses Unicode `‚Ä¶` (U+2026)_
    - _Preservation: Surrounding copy text and translations remain unchanged (3.5)_
    - _Requirements: 1.1, 2.1_

  - [x] 3.2 Add trailing `‚Ä¶` to `owner/repo` placeholders
    - Change `minePlaceholder: 'owner/repo'` ‚Ü?`'owner/repo‚Ä?` in both `labels.en` and `labels.zh`
    - Change `benchmarkPlaceholder: 'owner/repo'` ‚Ü?`'owner/repo‚Ä?` in both `labels.en` and `labels.zh`
    - _Bug_Condition: isBugCondition(placeholder) where placeholder lacks trailing `‚Ä¶`_
    - _Expected_Behavior: Placeholders display `owner/repo‚Ä¶`_
    - _Preservation: Input functionality unchanged (3.1)_
    - _Requirements: 1.7, 2.7_

  - [x] 3.3 Add `autocomplete="off"`, `name`, and `spellCheck={false}` to the "My repository" input
    - Locate the `<input>` for `mineInput` inside the `<label className="repo-benchmark-field">`
    - Add `autoComplete="off"` (React camelCase), `name="mine-repo"`, `spellCheck={false}`
    - _Bug_Condition: isBugCondition(input) where input lacks autocomplete/name/spellCheck_
    - _Expected_Behavior: Input has autoComplete="off", name="mine-repo", spellCheck={false}_
    - _Preservation: Input accepts text and updates mineInput state (3.1)_
    - _Requirements: 1.18, 2.18_

  - [x] 3.4 Add `autocomplete="off"`, `name`, and `spellCheck={false}` to all benchmark `<input>` fields
    - Locate the `<input>` inside the `.map()` for `visibleBenchmarkInputs`
    - Add `autoComplete="off"`, `name={`benchmark-repo-${index}`}`, `spellCheck={false}`
    - _Bug_Condition: isBugCondition(input) where benchmark inputs lack autocomplete/name/spellCheck_
    - _Expected_Behavior: Each benchmark input has autoComplete="off", unique name, spellCheck={false}_
    - _Preservation: Inputs accept text and call updateBenchmarkField (3.1)_
    - _Requirements: 1.18, 2.18_

  - [x] 3.5 Fix the "Include narrative" checkbox: add `id` and `htmlFor` association
    - Add `id="include-narrative"` to the `<input type="checkbox">` for `includeNarrative`
    - Add `htmlFor="include-narrative"` to the wrapping `<label>`
    - _Bug_Condition: isBugCondition(checkbox) where label lacks htmlFor and input lacks id_
    - _Expected_Behavior: Label is programmatically associated with checkbox via htmlFor/id_
    - _Preservation: Checkbox continues to toggle includeNarrative state on change (3.6)_
    - _Requirements: 1.22, 2.22_

  - [x] 3.6 Wrap the async benchmark loading state in `<div aria-live="polite">`
    - Locate the `loading-state` div that renders `{text.comparing}` during the initial fetch
    - Wrap it (or add `aria-live="polite"` directly to the container) so screen readers announce the status
    - _Bug_Condition: isBugCondition(loadingDiv) where loading region lacks aria-live_
    - _Expected_Behavior: Loading region has aria-live="polite"_
    - _Preservation: Loading text displays correctly (3.5)_
    - _Requirements: 1.23, 2.23_

  - [x] 3.7 Add `role="alert"` to the error `<div className="error-state">`
    - Locate the `<div className="error-state">` that renders `{error}` in the benchmark form section
    - Add `role="alert"` to that element
    - _Bug_Condition: isBugCondition(errorDiv) where error container lacks role="alert"_
    - _Expected_Behavior: Error container has role="alert" so screen readers announce errors_
    - _Preservation: Error message text and styling unchanged (3.9)_
    - _Requirements: 1.24, 2.24_

- [x] 4. Fix Compare.tsx ‚Ä?ellipsis, placeholder, input attributes, button type, img dimensions, role="alert"

  - [x] 4.1 Replace ASCII `...` with Unicode `‚Ä¶` in all loading/async copy strings
    - In `labels.en`: change `'Loading...'` ‚Ü?`'Loading‚Ä?`, `'Failed to load'` stays as-is (not a loading string)
    - In `labels.zh`: change `'Âä†ËΩΩ‰∏?..'` ‚Ü?`'Âä†ËΩΩ‰∏≠‚Ä?`
    - _Bug_Condition: isBugCondition(labels) where loading copy contains ASCII `...`_
    - _Expected_Behavior: Loading copy uses `‚Ä¶`_
    - _Preservation: Surrounding copy unchanged (3.5)_
    - _Requirements: 1.2, 2.2_

  - [x] 4.2 Add trailing `‚Ä¶` to the username input placeholder
    - Change `addUser: 'Add User'` ‚Ü?`'Add User‚Ä?` in `labels.en`
    - Change `addUser: 'Ê∑ªÂä†Áî®Êà∑'` ‚Ü?`'Ê∑ªÂä†Áî®Êà∑‚Ä?` in `labels.zh`
    - Note: `text.addUser` is used both as button label and placeholder ‚Ä?if they share the same key, add a separate `addUserPlaceholder` key or update only the placeholder usage
    - _Bug_Condition: isBugCondition(placeholder) where username placeholder lacks trailing `‚Ä¶`_
    - _Expected_Behavior: Placeholder displays `Add User‚Ä¶` / `Ê∑ªÂä†Áî®Êà∑‚Ä¶`_
    - _Preservation: Button label and input functionality unchanged (3.1)_
    - _Requirements: 1.8, 2.8_

  - [x] 4.3 Add `autocomplete="off"`, `name="username"`, and `spellCheck={false}` to the username `<input>`
    - Locate the `<input type="text">` with `value={inputValue}` in the compare input section
    - Add `autoComplete="off"`, `name="username"`, `spellCheck={false}`
    - _Bug_Condition: isBugCondition(input) where username input lacks autocomplete/name/spellCheck_
    - _Expected_Behavior: Input has autoComplete="off", name="username", spellCheck={false}_
    - _Preservation: Input accepts text, updates inputValue, triggers addUser on Enter (3.1)_
    - _Requirements: 1.19, 2.19_

  - [x] 4.4 Add `type="button"` to the "Add User" button
    - Locate `<button className="compare-add-btn" onClick={addUser}>` and add `type="button"`
    - _Bug_Condition: isBugCondition(button) where Add User button lacks type="button"_
    - _Expected_Behavior: Button has type="button"_
    - _Preservation: Button executes addUser handler on click (3.2)_
    - _Requirements: 1.27, 2.27_

  - [x] 4.5 Add `width` and `height` attributes to all `<img>` avatar elements
    - Locate `<img src={user.avatar_url} alt={user.username} className="compare-avatar" />` in the user cards loop
    - Add `width={40}` and `height={40}` (matching the CSS `.compare-avatar` size, verify in stylesheet)
    - _Bug_Condition: isBugCondition(img) where avatar img lacks width and height_
    - _Expected_Behavior: img has explicit width and height to prevent CLS_
    - _Preservation: Avatars render at same visual size defined by CSS (3.8)_
    - _Requirements: 1.13, 2.13_

  - [x] 4.6 Add `role="alert"` to both error `<div>` elements
    - Locate `<div className="error-state">` for the main error state
    - Locate `<div className="error-state">` for the partial failure state (`failedUsers`)
    - Add `role="alert"` to both
    - _Bug_Condition: isBugCondition(errorDiv) where error containers lack role="alert"_
    - _Expected_Behavior: Both error containers have role="alert"_
    - _Preservation: Error message text and styling unchanged (3.9)_
    - _Requirements: 1.25, 2.25_

- [x] 5. Fix Repositories.tsx ‚Ä?ellipsis, aria-hidden SVGs, img dimensions, input aria-label, select aria-label, repo card restructure

  - [x] 5.1 Replace ASCII `...` with Unicode `‚Ä¶` in all loading/async copy strings
    - In `labels.en`: change `'Loading...'` ‚Ü?`'Loading‚Ä?`, `'Analyzing repository...'` ‚Ü?`'Analyzing repository‚Ä?`
    - In `labels.zh`: change `'Âä†ËΩΩ‰∏?..'` ‚Ü?`'Âä†ËΩΩ‰∏≠‚Ä?`, `'Ê≠£Âú®ÂàÜÊûê‰ªìÂ∫ì...'` ‚Ü?`'Ê≠£Âú®ÂàÜÊûê‰ªìÂ∫ì‚Ä?`
    - _Bug_Condition: isBugCondition(labels) where loading copy contains ASCII `...`_
    - _Expected_Behavior: Loading copy uses `‚Ä¶`_
    - _Preservation: Surrounding copy unchanged (3.5)_
    - _Requirements: 1.3, 2.3_

  - [x] 5.2 Add `aria-hidden="true"` to star and fork decorative SVG icons
    - Locate the star SVG inside `<span className="repo-stat">` (polygon element)
    - Locate the fork SVG inside the second `<span className="repo-stat">` (circle/path elements)
    - Add `aria-hidden="true"` to both `<svg>` elements
    - _Bug_Condition: isBugCondition(svg) where decorative stat icons lack aria-hidden_
    - _Expected_Behavior: SVGs have aria-hidden="true"_
    - _Preservation: Icons render visually unchanged (3.10)_
    - _Requirements: 1.10, 2.10_

  - [x] 5.3 Add `width` and `height` to the user header `<img>` avatar
    - Locate `<img src={userData.avatar_url} alt={userData.username} className="header-avatar" />`
    - Add `width={32}` and `height={32}` (verify against `.header-avatar` CSS class)
    - _Bug_Condition: isBugCondition(img) where header avatar lacks width and height_
    - _Expected_Behavior: img has explicit width and height_
    - _Preservation: Avatar renders at same visual size (3.8)_
    - _Requirements: 1.14, 2.14_

  - [x] 5.4 Add `aria-label` to the search `<input>`
    - Locate `<input type="text" placeholder={text.searchPlaceholder} ... className="search-input" />`
    - Add `aria-label={text.searchPlaceholder}`
    - _Bug_Condition: isBugCondition(input) where search input lacks aria-label_
    - _Expected_Behavior: Search input has aria-label describing its purpose_
    - _Preservation: Input accepts text and updates searchTerm state (3.1)_
    - _Requirements: 1.20, 2.20_

  - [x] 5.5 Add `aria-label` to the sort `<select>`
    - Locate `<select value={sortBy} onChange={...} className="sort-select">`
    - Add `aria-label={text.sortBy ?? 'Sort by'}`
    - _Bug_Condition: isBugCondition(select) where sort select lacks aria-label_
    - _Expected_Behavior: Select has aria-label describing its purpose_
    - _Preservation: Select updates sortBy state on change (3.1)_
    - _Requirements: 1.21, 2.21_

  - [x] 5.6 Restructure repo cards: convert `<a>` wrapper to `<div>`, move repo link into standalone `<a>`, keep action buttons as siblings
    - Change `<a key={repo.url} href={repo.url} target="_blank" rel="noreferrer" className="repo-card">` to `<div key={repo.url} className="repo-card">`
    - Inside the card header, wrap `<h3 className="repo-card-name">{repo.name}</h3>` in a standalone `<a href={repo.url} target="_blank" rel="noreferrer">` so the repo name is the clickable link
    - Ensure the `<div className="repo-card-actions">` with the three buttons remains a sibling of the link, not nested inside it
    - Close the outer `<div>` at the end of the card (replacing the closing `</a>`)
    - _Bug_Condition: isBugCondition(card) where `<button>` elements are nested inside `<a>` tag_
    - _Expected_Behavior: Card is a `<div>`, repo name link is a standalone `<a>`, action buttons are siblings_
    - _Preservation: Repo URL opens in new tab via name link; analyze/benchmark/add-to-resume buttons fire their handlers (3.3)_
    - _Requirements: 1.30, 2.30_

- [x] 6. Fix Export.tsx ‚Ä?ellipsis, aria-hidden SVGs, img dimensions, aria-live, button types

  - [x] 6.1 Replace ASCII `...` with Unicode `‚Ä¶` in all loading/async copy strings
    - In `labels.en`: change `'Loading...'` ‚Ü?`'Loading‚Ä?`, `'Loading benchmark...'` ‚Ü?`'Loading benchmark‚Ä?`
    - In `labels.zh`: change `'Âä†ËΩΩ‰∏?..'` ‚Ü?`'Âä†ËΩΩ‰∏≠‚Ä?`, `'Âä†ËΩΩÂØπÊ†áÊä•Âëä‰∏?..'` ‚Ü?`'Âä†ËΩΩÂØπÊ†áÊä•Âëä‰∏≠‚Ä?`
    - _Bug_Condition: isBugCondition(labels) where loading copy contains ASCII `...`_
    - _Expected_Behavior: Loading copy uses `‚Ä¶`_
    - _Preservation: Surrounding copy unchanged (3.5)_
    - _Requirements: 1.4, 2.4_

  - [x] 6.2 Add `aria-hidden="true"` to all decorative export icon SVGs
    - Locate the PDF icon SVG inside `<div className="export-icon pdf-icon">`
    - Locate the card icon SVG inside `<div className="export-icon card-icon">`
    - Locate the markdown icon SVGs inside `<div className="export-icon markdown-icon">` (two instances)
    - Locate the benchmark section icon SVG
    - Add `aria-hidden="true"` to each `<svg>` element
    - _Bug_Condition: isBugCondition(svg) where export icon SVGs lack aria-hidden_
    - _Expected_Behavior: All decorative SVGs have aria-hidden="true"_
    - _Preservation: Icons render visually unchanged (3.10)_
    - _Requirements: 1.11, 2.11_

  - [x] 6.3 Add `width` and `height` to the social card `<img>` avatar
    - Locate `<img src={activeOutput.card_data.avatar_url} alt={activeOutput.card_data.username} className="social-card-avatar" />`
    - Add `width={48}` and `height={48}` (verify against `.social-card-avatar` CSS class)
    - _Bug_Condition: isBugCondition(img) where social card avatar lacks width and height_
    - _Expected_Behavior: img has explicit width and height_
    - _Preservation: Avatar renders at same visual size (3.8)_
    - _Requirements: 1.15, 2.15_

  - [x] 6.4 Wrap the async benchmark loading paragraph in `<div aria-live="polite">`
    - Locate the `{includeBenchmark && (...)}` section that renders `{benchmarkLoading && <p>{text.benchmarkLoading}</p>}`
    - Wrap the entire inner status block (loading, error, none, result paragraphs) in `<div aria-live="polite">`
    - _Bug_Condition: isBugCondition(loadingP) where benchmark loading paragraph lacks aria-live region_
    - _Expected_Behavior: Status region has aria-live="polite"_
    - _Preservation: Loading text displays correctly (3.5)_
    - _Requirements: 1.26, 2.26_

  - [x] 6.5 Add `type="button"` to the PDF download, card download, and copy markdown buttons
    - Locate `<button className="export-btn primary" onClick={exportPdf}>` ‚Ä?add `type="button"`
    - Locate `<button className="export-btn primary" onClick={downloadCard}>` ‚Ä?add `type="button"`
    - Locate `<button className="export-btn secondary" onClick={copyMarkdown}>` ‚Ä?add `type="button"`
    - Also add `type="button"` to the Retry button inside the pdfError block
    - _Bug_Condition: isBugCondition(button) where export action buttons lack type="button"_
    - _Expected_Behavior: All export action buttons have type="button"_
    - _Preservation: Buttons execute their respective handlers on click (3.2)_
    - _Requirements: 1.28, 2.28_

- [x] 7. Fix AIAnalysis.tsx ‚Ä?ellipsis, img dimensions, radar chart accessible label

  - [x] 7.1 Replace ASCII `...` with Unicode `‚Ä¶` in loading copy
    - In `labels.en`: change `'Analyzing...'` ‚Ü?`'Analyzing‚Ä?`
    - In `labels.zh`: change `'ÂàÜÊûê‰∏?..'` ‚Ü?`'ÂàÜÊûê‰∏≠‚Ä?`
    - _Bug_Condition: isBugCondition(labels) where loading copy contains ASCII `...`_
    - _Expected_Behavior: Loading copy uses `‚Ä¶`_
    - _Preservation: Surrounding copy unchanged (3.5)_
    - _Requirements: 1.5, 2.5_

  - [x] 7.2 Add `width` and `height` to the user header `<img>` avatar
    - Locate `<img src={userData.avatar_url} alt={userData.username} className="header-avatar" />`
    - Add `width={32}` and `height={32}` (verify against `.header-avatar` CSS class)
    - _Bug_Condition: isBugCondition(img) where header avatar lacks width and height_
    - _Expected_Behavior: img has explicit width and height_
    - _Preservation: Avatar renders at same visual size (3.8)_
    - _Requirements: 1.16, 2.16_

  - [x] 7.3 Wrap the `<ResponsiveContainer>` radar chart in a `<div role="img" aria-label="...">`
    - Locate the `<div className="radar-wrapper">` containing `<ResponsiveContainer>`
    - Wrap the `<ResponsiveContainer>` in `<div role="img" aria-label={language === 'zh' ? 'GitScore Èõ∑ËææÂõ? : 'GitScore radar chart'}>`
    - _Bug_Condition: isBugCondition(chart) where radar chart lacks role="img" and aria-label_
    - _Expected_Behavior: Chart container has role="img" and descriptive aria-label_
    - _Preservation: Chart renders visually with same data and styling (3.7)_
    - _Requirements: 1.31, 2.31_

- [x] 8. Fix Overview.tsx ‚Ä?ellipsis, history item div‚Üíbutton, aria-hidden SVGs, img dimensions, button types

  - [x] 8.1 Replace ASCII `...` with Unicode `‚Ä¶` in all loading/async copy strings
    - In `labels.en`: change `'Analyzing...'` ‚Ü?`'Analyzing‚Ä?` (analyzingRepo label)
    - In `labels.zh`: change `'ÂàÜÊûê‰∏?..'` ‚Ü?`'ÂàÜÊûê‰∏≠‚Ä?`
    - _Bug_Condition: isBugCondition(labels) where loading copy contains ASCII `...`_
    - _Expected_Behavior: Loading copy uses `‚Ä¶`_
    - _Preservation: Surrounding copy unchanged (3.5)_
    - _Requirements: 1.6, 2.6_

  - [x] 8.2 Convert `<div className="history-item-main" onClick={...}>` to `<button type="button">`
    - Locate `<div className="history-item-main" onClick={() => handleOpenAnalysis(item.username)} style={{ cursor: 'pointer' }}>`
    - Replace with `<button type="button" className="history-item-main" onClick={() => handleOpenAnalysis(item.username)}>`
    - Remove the `style={{ cursor: 'pointer' }}` (add CSS reset styles for the button if needed: `background: none; border: none; padding: 0; text-align: left; width: 100%;`)
    - _Bug_Condition: isBugCondition(element) where history item main area is a `<div onClick>` instead of `<button>`_
    - _Expected_Behavior: History item main area is a `<button type="button">` reachable by keyboard_
    - _Preservation: Activation navigates to AI Analysis page for the selected user (3.4)_
    - _Requirements: 1.9, 2.9_

  - [x] 8.3 Add `aria-hidden="true"` to all decorative SVG icons inside history action buttons
    - Locate all `<svg>` elements inside `<button className="history-action-btn">` elements (repos, AI analysis, compare, refresh cache, delete buttons)
    - Add `aria-hidden="true"` to each `<svg>`
    - _Bug_Condition: isBugCondition(svg) where history action button icons lack aria-hidden_
    - _Expected_Behavior: All decorative SVGs inside action buttons have aria-hidden="true"_
    - _Preservation: Icons render visually unchanged (3.10)_
    - _Requirements: 1.12, 2.12_

  - [x] 8.4 Add `width` and `height` to all history item `<img>` avatar elements
    - Locate `<img src={item.avatarUrl} alt={item.username} className="history-avatar" />` in the history list map
    - Add `width={32}` and `height={32}` (verify against `.history-avatar` CSS class)
    - _Bug_Condition: isBugCondition(img) where history avatar imgs lack width and height_
    - _Expected_Behavior: imgs have explicit width and height_
    - _Preservation: Avatars render at same visual size (3.8)_
    - _Requirements: 1.17, 2.17_

  - [x] 8.5 Add `type="button"` to action buttons missing it
    - Locate `<button className="history-action-btn" onClick={() => handleOpenRepos(currentUser)}>` in the candidates panel ‚Ä?add `type="button"`
    - Locate `<button className="history-action-btn" onClick={() => handleOpenRepos(currentUser)}>` in the resume builder header ‚Ä?add `type="button"`
    - Locate `<button className="history-action-btn added" onClick={...}>` (openExport) ‚Ä?add `type="button"`
    - Locate `<button className="clear-btn" onClick={clearHistory}>` ‚Ä?add `type="button"`
    - Locate all `<button className="history-action-btn">` elements in the history list that are missing `type="button"` (repos, AI analysis, compare, refresh, delete buttons)
    - _Bug_Condition: isBugCondition(button) where action buttons lack type="button"_
    - _Expected_Behavior: All action buttons have type="button"_
    - _Preservation: Buttons execute their respective handlers on click (3.2)_
    - _Requirements: 1.29, 2.29_

- [x] 9. Verify bug condition exploration test now passes

  - [x] 9.1 Re-run the SAME test from task 1 after all fixes are applied
    - **Property 1: Expected Behavior** - UI Guidelines Violations Resolved
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior for all six page components
    - Run `UIGuidelinesCompliance.test.tsx` on the FIXED code
    - **EXPECTED OUTCOME**: Test PASSES (confirms all violations are fixed)
    - _Requirements: 2.9, 2.13, 2.14, 2.15, 2.16, 2.17, 2.20, 2.27, 2.28, 2.29_

  - [x] 9.2 Verify preservation tests still pass
    - **Property 2: Preservation** - Functional Behavior Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2 on the FIXED code
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fixes (no regressions)

- [x] 10. Checkpoint - Ensure all tests pass
  - Run the full frontend test suite to confirm no regressions
  - Ensure all tests pass; ask the user if questions arise

