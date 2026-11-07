import { cp, mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const dist = join(root, "dist");
await mkdir(dist, { recursive: true });

for (const file of ["index.html", "styles.css", "app.js", "map-layout.js", "run-package.js", "pyodide-worker.js"]) {
  await cp(join(root, file), join(dist, file));
}

const modules = [
  "functions/__init__.py",
  "functions/types.py",
  "functions/inversion/__init__.py",
  "functions/inversion/baseline.py",
  "functions/equilibrium/__init__.py",
  "functions/equilibrium/model.py",
];
for (const file of modules) {
  const target = join(dist, "src/python", file);
  await mkdir(dirname(target), { recursive: true });
  await cp(join(root, "../src/python", file), target);
}
