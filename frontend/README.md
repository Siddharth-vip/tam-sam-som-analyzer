# AI TAM/SAM/SOM Market Analyzer — Frontend

Modern, high-performance React + TypeScript + Vite user interface for the AI TAM/SAM/SOM Market Analysis Platform.

## Features

- **Business Idea Extraction**: Intuitive input for unstructured business concepts with preset examples.
- **Visual Market Cards**: Prominent TAM, SAM, and SOM metric cards with uncertainty intervals and confidence indicators.
- **SOM Safety Compliance**: Strictly adheres to the backend rule: if SOM market share evidence is absent, SOM is clearly presented as "Insufficient Evidence" with explanatory rationale rather than fabricating monetary numbers.
- **Market Funnel**: Progressive narrowing visualization from Total Addressable Market down to Serviceable Addressable and Obtainable Market.
- **Top-Down vs. Bottom-Up Comparison**: Divergence severity classification (`ACCEPTABLE`, `WARNING`, `SEVERE_DIVERGENCE`), difference metrics, and narrative alignment explanation.
- **Calculation Audit Trail**: Expandable step-by-step mathematical trace displaying exact formulas, numerical operands, and source URLs.
- **Assumptions & Evidence Provenance**: Transparent distinction between user/heuristic assumptions and empirical evidence (with lifecycle stages: `DISCOVERED`, `FETCHED`, `EXTRACTED`, `VALIDATED`, `VERIFIED`).
- **Confidential Market Report & Export**: Comprehensive printable report format for export to PDF.

## Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Run unit and integration test suite
npm test

# Build production bundle
npm run build
```
