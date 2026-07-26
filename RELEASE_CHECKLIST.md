# Final Release Checklist

Before officially publishing the **Customer & Profitability Intelligence Platform** to your portfolio or GitHub, complete this final manual validation checklist to guarantee a true **10/10** recruiter experience:

### 1. Manual Feature Parity Verification
- [ ] Launch the application locally (`streamlit run dashboard/Home.py`).
- [ ] Verify the **Customer Analytics** tab (filters, scatter plots, LTV tables).
- [ ] Verify the **Market Intelligence** tab (global treemaps, region tables).
- [ ] Verify the **ML Risk Engine** tab (prediction histograms, inference outputs).

### 2. Docker Validation
- [ ] Start Docker Desktop (ensure the Docker daemon is running).
- [ ] Run `docker-compose up --build`.
- [ ] Verify the application launches at `http://localhost:8501` inside the container.

### 3. Visual Polish
- [ ] Take fresh, high-resolution screenshots of the new dashboard architecture.
- [ ] Create a short GIF navigating through the tabs.
- [ ] Place these visual assets in `docs/images/` and embed them in `README.md`.

### 4. Clean Clone Verification
- [ ] Clone the repository to a fresh directory.
- [ ] Follow the setup instructions in the README exactly as written.
- [ ] Run `pytest` on the fresh clone.
- [ ] Verify the environment works flawlessly without hidden local dependencies.

### 5. Tag Release
- [ ] Commit all changes.
- [ ] Tag the repository as `v2.0.0` (marking the DuckDB and CI/CD transition).
- [ ] Push to GitHub.
