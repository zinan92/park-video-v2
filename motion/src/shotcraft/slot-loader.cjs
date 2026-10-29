// webpack loader：只对 ShotCraft 原卡源码生效。把每个字符串字面量和 JSX 里的文字包成 __scT("原文")，
// 渲染时 __scT 按镜头给的对照表换成他的原话（表里没有的原样返回），原卡文件本身不改。
// 只在这些字的原位置上替换，其余源码一字不动（不重新打印整个文件，TypeScript 的打印器会把 JSX 文字印坏）。
const ts = require('typescript');

const named = (p, node) => (ts.isPropertyAssignment(p) || ts.isPropertySignature(p) || ts.isPropertyDeclaration(p)
  || ts.isMethodDeclaration(p) || ts.isEnumMember(p) || ts.isGetAccessor(p) || ts.isSetAccessor(p) || ts.isJsxAttribute(p)) && p.name === node;

const skip = (node) => {
  const p = node.parent;
  return !p || ts.isImportDeclaration(p) || ts.isExportDeclaration(p) || ts.isLiteralTypeNode(p) || ts.isExternalModuleReference(p)
    || ts.isModuleDeclaration(p) || ts.isExpressionStatement(p) || named(p, node);
};

const edits = (source, resourcePath) => {
  const file = ts.createSourceFile(resourcePath, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const edits = [];
  const call = (text) => `__scT(${JSON.stringify(text)})`;
  const walk = (node) => {
    if ((ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) && !skip(node) && /[A-Za-z一-鿿]/.test(node.text)) {
      edits.push([node.getStart(file), node.getEnd(), ts.isJsxAttribute(node.parent) ? `{${call(node.text)}}` : call(node.text)]);
      return;
    }
    if (ts.isJsxText(node) && node.text.trim()) {
      const raw = node.text;
      const lead = raw.match(/^\s*/)[0];
      const tail = raw.match(/\s*$/)[0];
      const keep = (ws) => (ws.includes('\n') ? '' : ws);  // JSX 里跨行的空白本来就不显示
      const inner = keep(lead) + raw.trim().replace(/\s+/g, ' ') + keep(tail);
      edits.push([node.getStart(file), node.getEnd(), `${lead.includes('\n') ? lead : ''}{${call(inner)}}${tail.includes('\n') ? tail : ''}`]);
      return;
    }
    ts.forEachChild(node, walk);
  };
  walk(file);
  return edits;
};

// 量卡时用：这个文件里所有会经过 __scT 的字（scripts/shotcraft.py 从里面挑出显示在画面上的，当文字槽）
module.exports.list = (source, resourcePath) => edits(source, resourcePath).map((e) => JSON.parse(e[2].replace(/^[\s{]*__scT\(|\)[}\s]*$/g, '')));

module.exports = Object.assign(function slotLoader(source) {
  const edits_ = edits(source, this.resourcePath);
  let out = source;
  for (const [a, z, text] of edits_.sort((x, y) => y[0] - x[0])) out = out.slice(0, a) + text + out.slice(z);
  return edits_.length ? `import { __scT } from ${JSON.stringify(require('path').join(__dirname, 'slot.ts'))};\n${out}` : out;
}, { list: module.exports.list });
