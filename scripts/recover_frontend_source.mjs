// Read-only recovery inventory/export. Never executes bundle or handoff code.
// The caller reviews emitted source and applies it to a separate project copy.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const root = path.resolve(process.argv[2]);
const files = new Map();
const hash = (text) => crypto.createHash("sha256").update(text).digest("hex");
function add(name, content, origin, priority) {
  name = name.replaceAll("\\", "/");
  name = name.replace(/^outputs\/frontend\//, "");
  if (!/^(src|tests)\/[\w./-]+$/.test(name) || name.split("/").includes("..")) return;
  if (!/\.(tsx?|jsx?|css)$/.test(name)) return;
  const old = files.get(name);
  if (!old || priority > old.priority) files.set(name, { name, content, origin, priority });
  else if (priority === old.priority && old.content !== content) {
    throw new Error(`Conflicting recovered source: ${name}`);
  }
}
const handoff = fs.readFileSync(path.join(root, "PROJECT_OCEAN_FRONTEND_HANDOFF.md"), "utf8").replaceAll("\r\n", "\n");
for (const section of handoff.matchAll(/^#{3,4} `([^`]+)`[^\n]*\n([\s\S]*?)(?=^#{1,4} |$(?![\s\S]))/gm)) {
  const block = section[2].match(/^```[^\n]*\n([\s\S]*?)^```/m);
  if (block) add(section[1], block[1], "historical_part6_handoff", 1);
}
function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const target = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(target);
    else if (/\.(js|css)$/.test(target)) {
      const bundle = fs.readFileSync(target, "utf8");
      for (const match of bundle.matchAll(/sourceMappingURL=data:application\/json[^,]*;base64,([A-Za-z0-9+/=]+)/g)) {
        let map;
        try { map = JSON.parse(Buffer.from(match[1], "base64").toString()); } catch { continue; }
        if (!String(map.file).includes("/./src/") || String(map.file).includes("node_modules")) continue;
        map.sources.forEach((source, index) => {
          const normalized = source.replaceAll("\\", "/");
          const start = normalized.lastIndexOf("/src/");
          const content = map.sourcesContent?.[index];
          if (start < 0 || !content || normalized.includes("__nextjs-internal-proxy")) return;
          const name = normalized.slice(start + 1);
          // CSS loader source maps can contain generated JS wrappers too.
          if (name.endsWith(".css")) return;
          add(name, content, "development_bundle_sourcesContent", 2);
        });
      }
    }
  }
}
walk(path.join(root, ".next/dev"));
const css = fs.readFileSync(path.join(root, ".next/dev/static/css/app/layout.css"), "utf8");
const headers = [...css.matchAll(/\/\*![\s\S]*?\*\//g)];
headers.forEach((header, index) => {
  const name = header[0].match(/\.\/src\/app\/(tokens|globals)\.css/);
  if (name) add(`src/app/${name[1]}.css`, css.slice(header.index + header[0].length, headers[index + 1]?.index ?? css.length).trim() + "\n", "development_css_bundle", 2);
});
for (const name of ["package.json", "package-lock.json", "next.config.ts", "tsconfig.json", "eslint.config.mjs", "next-env.d.ts", ".gitignore", "scripts/copy-cesium.mjs"]) {
  files.set(name, { name, content: fs.readFileSync(path.join(root, name), "utf8"), origin: "original_file", priority: 3 });
}
const requested = process.argv[3];
if (requested) {
  const entry = files.get(requested);
  if (!entry) throw new Error("Requested file not in recovery inventory");
  console.log(JSON.stringify(entry));
} else {
  console.log(JSON.stringify([...files.values()].map(({ content, ...entry }) => ({ ...entry, bytes: Buffer.byteLength(content), sha256: hash(content) })), null, 2));
}
