#include "ring_buffer_store.h"

#include <LittleFS.h>

RingBufferStore::RingBufferStore() : file_path_("/telemetry_queue.log"), max_records_(500) {}

bool RingBufferStore::begin(const String &file_path, size_t max_records) {
  file_path_ = file_path;
  max_records_ = max_records;
  if (!LittleFS.begin(true)) {
    Serial.println("[queue] failed to mount LittleFS");
    return false;
  }
  if (!LittleFS.exists(file_path_)) {
    File queue_file = LittleFS.open(file_path_, FILE_WRITE);
    if (!queue_file) {
      Serial.println("[queue] failed to initialize queue file");
      return false;
    }
    queue_file.close();
  }
  return true;
}

bool RingBufferStore::append(const String &payload) {
  std::vector<String> lines;
  if (!load_lines(lines)) {
    return false;
  }

  lines.push_back(payload);
  while (lines.size() > max_records_) {
    lines.erase(lines.begin());
  }
  return save_lines(lines);
}

bool RingBufferStore::peek_next(String &payload) {
  std::vector<String> lines;
  if (!load_lines(lines)) {
    return false;
  }
  if (lines.empty()) {
    return false;
  }
  payload = lines.front();
  return true;
}

bool RingBufferStore::pop_next() {
  std::vector<String> lines;
  if (!load_lines(lines)) {
    return false;
  }
  if (lines.empty()) {
    return false;
  }
  lines.erase(lines.begin());
  return save_lines(lines);
}

size_t RingBufferStore::size() {
  std::vector<String> lines;
  if (!load_lines(lines)) {
    return 0;
  }
  return lines.size();
}

bool RingBufferStore::load_lines(std::vector<String> &lines) {
  lines.clear();
  File queue_file = LittleFS.open(file_path_, FILE_READ);
  if (!queue_file) {
    return false;
  }

  while (queue_file.available()) {
    String line = queue_file.readStringUntil('\n');
    line.trim();
    if (line.length() > 0) {
      lines.push_back(line);
    }
  }
  queue_file.close();
  return true;
}

bool RingBufferStore::save_lines(const std::vector<String> &lines) {
  File queue_file = LittleFS.open(file_path_, FILE_WRITE);
  if (!queue_file) {
    return false;
  }

  for (const String &line : lines) {
    queue_file.println(line);
  }
  queue_file.close();
  return true;
}

