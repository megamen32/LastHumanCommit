import { existsSync } from 'node:fs';
import { createRequire } from 'node:module';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { GSDError, ErrorClassification } from './errors.js';
export const BUNDLED_GSD_TOOLS_PATH = fileURLToPath(new URL('../../get-shit-done/bin/gsd-tools.cjs', import.meta.url));
export const BUNDLED_CORE_CJS_PATH = fileURLToPath(new URL('../../get-shit-done/bin/lib/core.cjs', import.meta.url));
export const BUNDLED_GSD_TEMPLATES_DIR = fileURLToPath(new URL('../../get-shit-done/templates', import.meta.url));
export const BUNDLED_GSD_AGENTS_DIR = fileURLToPath(new URL('../../agents', import.meta.url));
const LEGACY_ASSET_SUBPATH = {
    'gsd-tools': 'gsd-tools.cjs',
    'core-cjs': join('lib', 'core.cjs'),
};
const BUNDLED_LEGACY_ASSET_PATH = {
    'gsd-tools': BUNDLED_GSD_TOOLS_PATH,
    'core-cjs': BUNDLED_CORE_CJS_PATH,
};
export function resolveLegacyInstallDir(homeDir = homedir()) {
    return join(homeDir, '.claude', 'get-shit-done');
}
export function resolveLegacyTemplatesDir(homeDir = homedir()) {
    return join(resolveLegacyInstallDir(homeDir), 'templates');
}
export function resolveLegacyWorkflowsDir(homeDir = homedir()) {
    return join(resolveLegacyInstallDir(homeDir), 'workflows');
}
export function resolveLegacyUserProfilePath(homeDir = homedir()) {
    return join(resolveLegacyInstallDir(homeDir), 'USER-PROFILE.md');
}
export function resolveLegacySkillsDir(homeDir = homedir()) {
    return join(resolveLegacyInstallDir(homeDir), 'skills');
}
export function resolveBundledTemplatesDir() {
    return BUNDLED_GSD_TEMPLATES_DIR;
}
export function resolveBundledAgentsDir() {
    return BUNDLED_GSD_AGENTS_DIR;
}
function legacyAssetProbes(asset, projectDir, homeDir) {
    const suffix = LEGACY_ASSET_SUBPATH[asset];
    return [
        BUNDLED_LEGACY_ASSET_PATH[asset],
        join(projectDir, '.claude', 'get-shit-done', 'bin', suffix),
        join(homeDir, '.claude', 'get-shit-done', 'bin', suffix),
    ];
}
export function probeLegacySdkAsset(asset, projectDir, deps = {}) {
    const pathExists = deps.existsSync ?? existsSync;
    const probes = legacyAssetProbes(asset, projectDir, deps.homeDir ?? homedir());
    return {
        asset,
        path: probes.find(candidate => pathExists(candidate)) ?? null,
        fallbackPath: probes[probes.length - 1],
        probes,
    };
}
/**
 * Resolve the legacy `gsd-tools.cjs` executable path through the SDK Package Seam Module.
 *
 * Preserves historical behavior: if no probe exists, return the final fallback path so
 * downstream subprocess errors still show a concrete location.
 */
export function resolveGsdToolsPath(projectDir, deps = {}) {
    const resolution = probeLegacySdkAsset('gsd-tools', projectDir, deps);
    return resolution.path ?? resolution.fallbackPath;
}
function missingLegacyCoreMessage(resolution) {
    return [
        'state load: get-shit-done/bin/lib/core.cjs not found.',
        `Checked: ${resolution.probes.join(', ')}`,
        'Install GSD (e.g. npm i -g get-shit-done-cc) or clone with get-shit-done next to the SDK.',
    ].join(' ');
}
/**
 * Load `loadConfig(cwd)` from the legacy CJS install through one compatibility seam.
 */
export function loadLegacyCoreConfig(projectDir, deps = {}) {
    const resolution = probeLegacySdkAsset('core-cjs', projectDir, deps);
    if (!resolution.path) {
        throw new GSDError(missingLegacyCoreMessage(resolution), ErrorClassification.Blocked);
    }
    const req = (deps.createRequire ?? createRequire)(import.meta.url);
    const mod = req(resolution.path);
    if (typeof mod.loadConfig !== 'function') {
        throw new GSDError(`state load: invalid core.cjs at ${resolution.path} (missing loadConfig(cwd)).`, ErrorClassification.Blocked);
    }
    return mod.loadConfig(projectDir);
}
//# sourceMappingURL=sdk-package-compatibility.js.map