// Copyright 2021 The Pigweed Authors
//
// Licensed under the Apache License, Version 2.0 (the "License"); you may not
// use this file except in compliance with the License. You may obtain a copy of
// the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
// WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
// License for the specific language governing permissions and limitations under
// the License.
#pragma once

#include "pw_assert/assert.h"
#include "pw_containers/intrusive_list.h"
#include "pw_status/status.h"
#include "pw_stream/stream.h"

namespace pw::transfer {
namespace internal {

// The internal::Handler class is the base class for the transfer handler
// classes. Transfer handlers connect a transfer ID to the functions that do the
// actual reads and/or writes.
//
// Handlers use a stream::Reader or stream::Writer to do the reads and writes.
// They also provide optional Prepare and Finalize functions.
class Handler : public IntrusiveList<Handler>::Item {
 public:
  virtual ~Handler() = default;

  constexpr uint32_t id() const { return transfer_id_; }

  // Called at the beginning of a read transfer. The stream::Reader must be
  // ready to read after a successful PrepareRead() call. Returning a non-OK
  // status aborts the read.
  //
  // Status::Unimplemented() indicates that reads are not supported.
  virtual Status PrepareRead() = 0;

  // FinalizeRead() is called at the end of a read transfer. The status argument
  // indicates whether the data transfer was successful or not.
  virtual void FinalizeRead(Status) {}

  // Called at the beginning of a write transfer. The stream::Writer must be
  // ready to read after a successful PrepareRead() call. Returning a non-OK
  // status aborts the write.
  //
  // Status::Unimplemented() indicates that writes are not supported.
  virtual Status PrepareWrite() = 0;

  // FinalizeWrite() is called at the end of a write transfer. The status
  // argument indicates whether the data transfer was successful or not.
  //
  // Returning an error signals that the transfer failed, even if it had
  // succeeded up to this point.
  virtual Status FinalizeWrite(Status) { return OkStatus(); }

 protected:
  constexpr Handler(uint32_t transfer_id, stream::Reader* reader)
      : transfer_id_(transfer_id), reader_(reader) {}

  constexpr Handler(uint32_t transfer_id, stream::Writer* writer)
      : transfer_id_(transfer_id), writer_(writer) {}

  void set_reader(stream::Reader& reader) { reader_ = &reader; }
  void set_writer(stream::Writer& writer) { writer_ = &writer; }

 private:
  // Only valid after a PrepareRead() call that returns OK.
  stream::Reader& reader() const {
    PW_DASSERT(reader_ != nullptr);
    return *reader_;
  }

  // Only valid after a PrepareWrite() call that returns OK.
  stream::Writer& writer() const {
    PW_DASSERT(writer_ != nullptr);
    return *writer_;
  }

  uint32_t transfer_id_;

  // Use a union to support constexpr construction.
  union {
    stream::Reader* reader_;
    stream::Writer* writer_;
  };
};

}  // namespace internal

class ReadOnlyHandler : public internal::Handler {
 public:
  constexpr ReadOnlyHandler(uint32_t transfer_id)
      : internal::Handler(transfer_id, static_cast<stream::Reader*>(nullptr)) {}

  constexpr ReadOnlyHandler(uint32_t transfer_id, stream::Reader& reader)
      : internal::Handler(transfer_id, &reader) {}

  Status PrepareRead() override { return OkStatus(); }

  // Writes are not supported.
  Status PrepareWrite() final { return Status::Unimplemented(); }

  using internal::Handler::set_reader;
};

class WriteOnlyHandler : public internal::Handler {
 public:
  constexpr WriteOnlyHandler(uint32_t transfer_id)
      : internal::Handler(transfer_id, static_cast<stream::Writer*>(nullptr)) {}

  constexpr WriteOnlyHandler(uint32_t transfer_id, stream::Writer& writer)
      : internal::Handler(transfer_id, &writer) {}

  // Reads are not supported.
  Status PrepareRead() final { return Status::Unimplemented(); }

  Status PrepareWrite() override { return OkStatus(); }

  using internal::Handler::set_writer;
};

class ReadWriteHandler : public internal::Handler {
 public:
  constexpr ReadWriteHandler(uint32_t transfer_id)
      : internal::Handler(transfer_id, static_cast<stream::Reader*>(nullptr)) {}
  constexpr ReadWriteHandler(uint32_t transfer_id,
                             stream::ReaderWriter& reader_writer)
      : internal::Handler(transfer_id,
                          static_cast<stream::Reader*>(&reader_writer)) {}

  // Both reads and writes are supported.
  Status PrepareRead() override { return OkStatus(); }
  Status PrepareWrite() override { return OkStatus(); }

  void set_reader_writer(stream::ReaderWriter& reader_writer) {
    set_reader(reader_writer);
  }
};

}  // namespace pw::transfer