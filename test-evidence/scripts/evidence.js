'use strict';

const fs = require('fs');
const path = require('path');

function pad(value, width = 2) {
  return String(value).padStart(width, '0');
}

function timecode(ms) {
  const total = Math.max(0, Math.round(ms));
  const hours = Math.floor(total / 3600000);
  const minutes = Math.floor((total % 3600000) / 60000);
  const seconds = Math.floor((total % 60000) / 1000);
  return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}.${pad(total % 1000, 3)}`;
}

class TestEvidence {
  constructor({ output, meta = {} } = {}) {
    if (!output) throw new Error('TestEvidence requires an output path');
    this.output = path.resolve(output);
    this.meta = meta;
    this.startedAt = new Date();
    this.t0 = Date.now();
    this.page = null;
    this.steps = [];
    this.assertions = [];
    this.marks = [];
    this.console = [];
    this.failedRequests = [];
  }

  elapsed() {
    return Date.now() - this.t0;
  }

  timecode(ms = this.elapsed()) {
    return timecode(ms);
  }

  attach(page) {
    this.page = page;

    page.on('console', (msg) => {
      if (msg.type() !== 'error') return;
      if (this.console.length < 500) {
        this.console.push({ type: 'error', text: msg.text(), ms: this.elapsed() });
      }
    });

    page.on('pageerror', (err) => {
      if (this.console.length < 500) {
        this.console.push({
          type: 'pageerror',
          text: String((err && err.message) || err),
          ms: this.elapsed(),
        });
      }
    });

    page.on('requestfailed', (request) => {
      if (this.failedRequests.length < 500) {
        this.failedRequests.push({
          url: request.url(),
          method: request.method(),
          failure: (request.failure() && request.failure().errorText) || '',
          ms: this.elapsed(),
        });
      }
    });
  }

  mark(label) {
    const item = { label, ms: this.elapsed() };
    this.marks.push(item);
    return item;
  }

  async step(id, name, action, { caseId = null } = {}) {
    const record = {
      id,
      name,
      caseId,
      startMs: this.elapsed(),
      endMs: null,
      status: 'done',
      error: null,
    };
    try {
      const result = await action();
      record.endMs = this.elapsed();
      this.steps.push(record);
      return result;
    } catch (error) {
      record.endMs = this.elapsed();
      record.status = 'error';
      record.error = String((error && error.message) || error).split('\n')[0];
      this.steps.push(record);
      throw error;
    }
  }

  async assert(id, name, check, options = {}) {
    const record = {
      id,
      name,
      caseId: options.caseId || null,
      expected: options.expected || null,
      defect: options.defect || null,
      verdict: 'pass',
      startMs: this.elapsed(),
      endMs: null,
      error: null,
      screenshot: null,
    };

    try {
      await check();
    } catch (error) {
      record.verdict = 'fail';
      record.error = String((error && error.message) || error).split('\n')[0];
      if (options.screenshot !== false && this.page) {
        try {
          record.screenshot = await this.screenshot(`fail-${id}`);
        } catch (_) {}
      }
    }

    record.endMs = this.elapsed();
    this.assertions.push(record);

    if (options.fatal === true && record.verdict === 'fail') {
      throw new Error(`${id} failed: ${record.error}`);
    }
    return record;
  }

  async screenshot(label) {
    if (!this.page) return null;
    const dir = path.join(path.dirname(this.output), 'shots');
    fs.mkdirSync(dir, { recursive: true });
    const safe = String(label).replace(/[^\w.-]+/g, '-').slice(0, 80);
    const file = path.join(dir, `${Date.now()}-${safe}.png`);
    await this.page.screenshot({ path: file });
    return file;
  }

  summary() {
    const pass = this.assertions.filter((item) => item.verdict === 'pass').length;
    const fail = this.assertions.filter((item) => item.verdict === 'fail').length;
    return {
      pass,
      fail,
      total: this.assertions.length,
      steps: this.steps.length,
      consoleErrors: this.console.length,
      failedRequests: this.failedRequests.length,
    };
  }

  async finish(extra = {}) {
    const data = {
      schema: 'test-evidence/1',
      startedAt: this.startedAt.toISOString(),
      finishedAt: new Date().toISOString(),
      durationMs: this.elapsed(),
      meta: this.meta,
      ...extra,
      summary: this.summary(),
      steps: this.steps,
      assertions: this.assertions,
      console: this.console,
      failedRequests: this.failedRequests,
      marks: this.marks,
    };
    fs.mkdirSync(path.dirname(this.output), { recursive: true });
    fs.writeFileSync(this.output, `${JSON.stringify(data, null, 2)}\n`, 'utf8');
    return data;
  }
}

module.exports = { TestEvidence, timecode };