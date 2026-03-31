import '@testing-library/jest-dom'

// jsdom doesn't implement scrollIntoView — stub it so App's chip-click
// timeout doesn't throw an unhandled exception during tests.
window.HTMLElement.prototype.scrollIntoView = () => {}
