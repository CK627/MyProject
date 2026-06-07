<?php
header('Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
header('Content-Disposition: attachment; filename="导入模板.xlsx"');
header('Cache-Control: no-cache, no-store, must-revalidate');
header('Pragma: no-cache');
header('Expires: 0');
if (!class_exists('ZipArchive')) { http_response_code(500); echo 'ZipArchive not available'; exit; }
$tmp = tempnam(sys_get_temp_dir(), 'xlsx');
$zip = new ZipArchive();
if ($zip->open($tmp, ZipArchive::OVERWRITE) !== true) { http_response_code(500); echo 'cannot open zip'; exit; }
$zip->addFromString('[Content_Types].xml',
  '<?xml version="1.0" encoding="UTF-8"?>'
  .'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
  .'<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
  .'<Default Extension="xml" ContentType="application/xml"/>'
  .'<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
  .'<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
  .'<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
  .'</Types>'
);
$zip->addFromString('_rels/.rels',
  '<?xml version="1.0" encoding="UTF-8"?>'
  .'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
  .'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
  .'</Relationships>'
);
$zip->addFromString('xl/workbook.xml',
  '<?xml version="1.0" encoding="UTF-8"?>'
  .'<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
  .'<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>'
  .'</workbook>'
);
$zip->addFromString('xl/_rels/workbook.xml.rels',
  '<?xml version="1.0" encoding="UTF-8"?>'
  .'<Relationships xmlns="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
  .'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
  .'<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
  .'</Relationships>'
);
$zip->addFromString('xl/sharedStrings.xml',
  '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
  .'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="2" uniqueCount="2">'
  .'<si><t>学号</t></si>'
  .'<si><t>姓名</t></si>'
  .'</sst>'
);
$zip->addFromString('xl/worksheets/sheet1.xml',
  '<?xml version="1.0" encoding="UTF-8"?>'
  .'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
  .'<sheetData>'
  .'<row r="1">'
  .'<c r="A1" t="s"><v>0</v></c>'
  .'<c r="B1" t="s"><v>1</v></c>'
  .'</row>'
  .'</sheetData>'
  .'</worksheet>'
);
$zip->close();
readfile($tmp);
@unlink($tmp);
