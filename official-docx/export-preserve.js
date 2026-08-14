#!/usr/bin/env node
const { Document, Packer, Paragraph, TextRun, AlignmentType } = require('docx');
const fs = require('fs');
const path = require('path');

const SIZE_ERHAO = 44;
const SIZE_SANHAO = 32;
const LINE_SPACING = 574;
const FIRST_LINE_INDENT = 640;

const marginTop = Math.round(3.7 * 567);
const marginBottom = Math.round(3.5 * 567);
const marginLeft = Math.round(2.8 * 567);
const marginRight = Math.round(2.6 * 567);

function createTitle(text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 0, after: 300, line: LINE_SPACING, lineRule: "exact" },
    indent: { left: 1280, right: 1280 },
    children: [new TextRun({ text, font: "方正小标宋简体", size: SIZE_ERHAO })]
  });
}

function createBodyParagraph(text) {
  const children = [];
  const boldRegex = /\*\*(.+?)\*\*/g;
  let lastIndex = 0;
  let match;

  while ((match = boldRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      children.push(new TextRun({ text: text.slice(lastIndex, match.index), font: "仿宋_GB2312", size: SIZE_SANHAO }));
    }
    children.push(new TextRun({ text: match[1], font: "黑体", size: SIZE_SANHAO, bold: true }));
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) {
    children.push(new TextRun({ text: text.slice(lastIndex), font: "仿宋_GB2312", size: SIZE_SANHAO }));
  }

  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { line: LINE_SPACING, lineRule: "exact" },
    indent: { firstLine: FIRST_LINE_INDENT },
    children: children.length > 0 ? children : [new TextRun({ text, font: "仿宋_GB2312", size: SIZE_SANHAO })]
  });
}

const args = process.argv.slice(2);
const argMap = {};
for (let i = 0; i < args.length; i += 2) {
  if (args[i].startsWith('--')) argMap[args[i]] = args[i + 1];
}

const title = argMap['--title'];
const mdPath = argMap['--content-file'];
const outputPath = argMap['--output'];

const content = fs.readFileSync(mdPath, 'utf-8');
const lines = content.split('\n');

const children = [createTitle(title)];

for (const line of lines) {
  const trimmed = line.trim();
  if (!trimmed) continue;
  if (/^#\s/.test(trimmed)) continue; // skip markdown title

  // unescape \. \* etc.
  let text = trimmed.replace(/\\([\.\*\+\-\!\[\]\(\)\`\#\>])/g, '$1');

  // remove leading - or * list markers (keep content)
  text = text.replace(/^[\-\*]\s+/, '');

  children.push(createBodyParagraph(text));
}

const doc = new Document({
  sections: [{
    properties: {
      page: { margin: { top: marginTop, right: marginRight, bottom: marginBottom, left: marginLeft } }
    },
    children
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(outputPath, buffer);
  console.log('公文Word文档已生成：' + outputPath);
});
