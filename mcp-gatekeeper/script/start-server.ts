#!/usr/bin/env node
/**
 * MCP Gatekeeper Server - Startup Script
 *
 * Main entry point to boot up the FastMCP-based MCP Gatekeeper server.
 * Handles compilation, service startup, and graceful shutdown.
 */

import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';
import { execSync } from 'child_process';
import { Chain as FastMCP } from 'fastmcp';

// Get project root
const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(__dirname, '..');

/**
 * Compile TypeScript to JavaScript
 */
async function build(): Promise<void> {
  try {
    console.log('Building project...');
    execSync('npx tsc', { cwd: projectRoot, stdio: 'inherit' });
    console.log('Build complete.');
  } catch (err) {
    console.error('Build failed.');
    process.exit(1);
  }
}

/**
 * Clear build artifacts
 */
async function clean(): Promise<void> {
  try {
    const { glob, rm } = await import('glob');
    const files = await glob('dist/**/*.js', { absolute: true });
    await Promise.all(files.map(f => rm(f)));
    console.log('Clean complete.');
  } catch (err) {
    // Directory might not exist yet
    console.log('Clean: no built files found.');
  }
}

/**
 * Type-check project
 */
async function typeCheck(): Promise<void> {
  try {
    console.log('Type checking...');
    execSync('npx tsc --noEmit', { cwd: projectRoot, stdio: 'inherit' });
    console.log('Type check: OK');
  } catch (err) {
    console.error('Type check: FAILED');
    process.exit(1);
  }
}

/**
 * ===================================================================
 *  Main
 * ===================================================================
 */

async function main(): Promise<void> {
  const args = process.argv.slice(2);

  const command = args.find((a) => ['build', 'clean', 'type-check', 'start', 'dev'].includes(a));

  switch (command) {
    case 'build':
      await build();
      break;
    case 'clean':
      await clean();
      break;
    case 'type-check':
      await typeCheck();
      break;
    case 'start':
    case 'dev':
      // Start the MCP server
      startMcpServer();
      break;
    default:
      // Default: start the server
      startMcpServer();
  }
}

/**
 * Start the MCP Gatekeeper server
 */
function startMcpServer(): void {
  const { spawn } = require('child_process');
  const src = './dist/index.js';

  const proc = spawn('node', [src], {
    cwd: projectRoot,
    env: { ...process.env },
    stdio: 'inherit',
  });

  proc.on('error', (err) => {
    console.error(`Failed to start MCP server: ${err.message}`);
    process.exit(1);
  });

  proc.on('close', (code) => {
    process.exit(code ?? 0);
  });
}

// Run main
main();
