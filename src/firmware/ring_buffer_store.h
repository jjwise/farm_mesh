#pragma once

#include <Arduino.h>

#include <vector>

class RingBufferStore {
 public:
  RingBufferStore();
  bool begin(const String &file_path, size_t max_records);
  bool append(const String &payload);
  bool peek_next(String &payload);
  bool pop_next();
  size_t size();

 private:
  bool load_lines(std::vector<String> &lines);
  bool save_lines(const std::vector<String> &lines);

  String file_path_;
  size_t max_records_;
};

