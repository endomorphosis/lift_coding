import { execSync } from 'child_process';
import { readFileSync, writeFileSync } from 'fs';
import { join } from 'path';

function run(payload) {
  const { source, target } = payload;
  
  // Read the source file
  const sourceContent = readFileSync(source, 'utf-8');
  
  // Parse the source content to extract the random segment
  const parsed = JSON.parse(sourceContent);
  
  // Extract the leaked random segment
  const leakedSegment = parsed.value;
  
  // Write the leaked segment to the target file
  writeFileSync(target, leakedSegment);
  
  // Return the result
  return leakedSegment;
}

function run(payload) {
  const { source, target } = payload;
  
  // Read the source file
  const sourceContent = readFileSync(source, 'utf-4');
  
  // Parse the source content to extract the random segment
  const parsed = JSON.parse(sourceContent);
  
  // Extract the leaked random segment
  const leakedSegment = parsed.value;
  
  // Write the leaked segment to the target file
  writeFileSync(target, leakedSegment);
  
  // Return the result
  return leakedSegment;
}

function run(payload) {
  const { source, target } = payload;
  
  // Read the source file
  const sourceContent = readFileSync(source, 'utf-8');
  
  // Parse the source content to extract the random segment
  const parsed = JSON.parse(sourceContent);
  
  // Extract the leaked random segment
  const leakedSegment = parsed.value;
  
  // Write the leaked segment to the target file
  writeFileSync(target, leakedSegment);
  
  // Return the result
  return leakedSegment;
}

function run(payload) {
  const { source, target } = payload;
  
  // Read the source file
  const sourceContent = readFileSync(source, 'utf-8');
  
  // Parse the source content to extract the random segment
  const parsed = JSON.parse(sourceContent);
  
  // Extract the leaked random segment
  const leakedSegment = parsed.value;
  
  // Write the leaked segment to the target file
  writeFileSync(target, leakedSegment);
  
  // Return the result
  return leakedSegment;
}