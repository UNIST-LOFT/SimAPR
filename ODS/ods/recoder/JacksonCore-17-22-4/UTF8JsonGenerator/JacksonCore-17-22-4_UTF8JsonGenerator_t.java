package com.fasterxml.jackson.core.json;

import java.io.*;
import java.math.BigDecimal;
import java.math.BigInteger;

import com.fasterxml.jackson.core.*;
import com.fasterxml.jackson.core.io.*;

public class UTF8JsonGenerator
    extends JsonGeneratorImpl
{
    private final static byte BYTE_u = (byte) 'u';

    private final static byte BYTE_0 = (byte) '0';

    private final static byte BYTE_LBRACKET = (byte) '[';
    private final static byte BYTE_RBRACKET = (byte) ']';
    private final static byte BYTE_LCURLY = (byte) '{';
    private final static byte BYTE_RCURLY = (byte) '}';

    private final static byte BYTE_BACKSLASH = (byte) '\\';
    private final static byte BYTE_COMMA = (byte) ',';
    private final static byte BYTE_COLON = (byte) ':';
    private final static byte BYTE_QUOTE = (byte) '"';

    // intermediate copies only made up to certain length...
    private final static int MAX_BYTES_TO_BUFFER = 512;

    private final static byte[] HEX_CHARS = CharTypes.copyHexBytes();

    private final static byte[] NULL_BYTES = { 'n', 'u', 'l', 'l' };
    private final static byte[] TRUE_BYTES = { 't', 'r', 'u', 'e' };
    private final static byte[] FALSE_BYTES = { 'f', 'a', 'l', 's', 'e' };

    /*
    /**********************************************************
    /* Output buffering
    /**********************************************************
     */

    /**
     * Underlying output stream used for writing JSON content.
     */
    final protected OutputStream _outputStream;

    /**
     * Intermediate buffer in which contents are buffered before
     * being written using {@link #_outputStream}.
     */
    protected byte[] _outputBuffer;

    /**
     * Pointer to the position right beyond the last character to output
     * (end marker; may be past the buffer)
     */
    protected int _outputTail;

    /**
     * End marker of the output buffer; one past the last valid position
     * within the buffer.
     */
    protected final int _outputEnd;

    /**
     * Maximum number of <code>char</code>s that we know will always fit
     * in the output buffer after escaping
     */
    protected final int _outputMaxContiguous;

    /**
     * Intermediate buffer in which characters of a String are copied
     * before being encoded.
     */
    protected char[] _charBuffer;

    /**
     * Length of <code>_charBuffer</code>
     */
    protected final int _charBufferLength;

    /**
     * 6 character temporary buffer allocated if needed, for constructing
     * escape sequences
     */
    protected byte[] _entityBuffer;

    /**
     * Flag that indicates whether the output buffer is recycable (and
     * needs to be returned to recycler once we are done) or not.
     */
    protected boolean _bufferRecyclable;

    /*
    /**********************************************************
    /* Life-cycle
    /**********************************************************
     */

    public UTF8JsonGenerator(IOContext ctxt, int features, ObjectCodec codec,
            OutputStream out)
    {
        super(ctxt, features, codec);
        _outputStream = out;
        _bufferRecyclable = true;
        _outputBuffer = ctxt.allocWriteEncodingBuffer();
        _outputEnd = _outputBuffer.length;

        /* To be exact, each char can take up to 6 bytes when escaped (Unicode
         * escape with backslash, 'u' and 4 hex digits); but to avoid fluctuation,
         * we will actually round down to only do up to 1/8 number of chars
         */
        _outputMaxContiguous = _outputEnd >> 3;
        _charBuffer = ctxt.allocConcatBuffer();
        _charBufferLength = _charBuffer.length;

        // By default we use this feature to determine additional quoting
        if (isEnabled(Feature.ESCAPE_NON_ASCII)) {
            setHighestNonEscapedChar(127);
        }
    }
    
    public UTF8JsonGenerator(IOContext ctxt, int features, ObjectCodec codec,
            OutputStream out,
            byte[] outputBuffer, int outputOffset, boolean bufferRecyclable)
    {
        
        super(ctxt, features, codec);
        _outputStream = out;
        _bufferRecyclable = bufferRecyclable;
        _outputTail = outputOffset;
        _outputBuffer = outputBuffer;
        _outputEnd = _outputBuffer.length;
        // up to 6 bytes per char (see above), rounded up to 1/8
        _outputMaxContiguous = (_outputEnd >> 3);
        _charBuffer = ctxt.allocConcatBuffer();
        _charBufferLength = _charBuffer.length;
    }

    /*
    /**********************************************************
    /* Overridden configuration methods
    /**********************************************************
     */
    
    @Override
    public Object getOutputTarget() {
        return _outputStream;
    }

    @Override
    public int getOutputBuffered() {
        // Assuming tail is always valid, set to 0 on close
        return _outputTail;
    }

    /*
    /**********************************************************
    /* Overridden methods
    /**********************************************************
     */

    @Override
    public void writeFieldName(String name)  throws IOException
    {
        if (_cfgPrettyPrinter != null) {
            _writePPFieldName(name);
            return;
        }
        final int status = _writeContext.writeFieldName(name);
        if (status == JsonWriteContext.STATUS_EXPECT_VALUE) {
            _reportError("Can not write a field name, expecting a value");
        }
        if (status == JsonWriteContext.STATUS_OK_AFTER_COMMA) { // need comma
            if (_outputTail >= _outputEnd) {
                _flushBuffer();
            }
            _outputBuffer[_outputTail++] = BYTE_COMMA;
        }
        /* To support [JACKSON-46], we'll do this:
         * (Question: should quoting of spaces (etc) still be enabled?)
         */
        if (_cfgUnqNames) {
            _writeStringSegments(name, false);
            return;
        }
        final int len = name.length();
        // Does it fit in buffer?
        if (len > _charBufferLength) { // no, offline
            _writeStringSegments(name, true);
            return;
        }
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
        // But as one segment, or multiple?
        if (len <= _outputMaxContiguous) {
            if ((_outputTail + len) > _outputEnd) { // caller must ensure enough space
                _flushBuffer();
            }
            _writeStringSegment(name, 0, len);
        } else {
            _writeStringSegments(name, 0, len);
        }
        // and closing quotes; need room for one more char:
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
    }
    
    @Override
    public void writeFieldName(SerializableString name) throws IOException
    {
        if (_cfgPrettyPrinter != null) {
            _writePPFieldName(name);
            return;
        }
        final int status = _writeContext.writeFieldName(name.getValue());
        if (status == JsonWriteContext.STATUS_EXPECT_VALUE) {
            _reportError("Can not write a field name, expecting a value");
        }
        if (status == JsonWriteContext.STATUS_OK_AFTER_COMMA) {
            if (_outputTail >= _outputEnd) {
                _flushBuffer();
            }
            _outputBuffer[_outputTail++] = BYTE_COMMA;
        }
        if (_cfgUnqNames) {
            _writeUnq(name);
            return;
        }
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
        int len = name.appendQuotedUTF8(_outputBuffer, _outputTail);
        if (len < 0) { // couldn't append, bit longer processing
            _writeBytes(name.asQuotedUTF8());
        } else {
            _outputTail += len;
        }
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
    }    

    private final void _writeUnq(SerializableString name) throws IOException {
        int len = name.appendQuotedUTF8(_outputBuffer, _outputTail);
        if (len < 0) {
            _writeBytes(name.asQuotedUTF8());
        } else {
            _outputTail += len;
        }
    }
    
    /*
    /**********************************************************
    /* Output method implementations, structural
    /**********************************************************
     */

    @Override
    public final void writeStartArray() throws IOException
    {
        _verifyValueWrite("start an array");
        _writeContext = _writeContext.createChildArrayContext();
        if (_cfgPrettyPrinter != null) {
            _cfgPrettyPrinter.writeStartArray(this);
        } else {
            if (_outputTail >= _outputEnd) {
                _flushBuffer();
            }
            _outputBuffer[_outputTail++] = BYTE_LBRACKET;
        }
    }

    @Override
    public final void writeEndArray() throws IOException
    {
        if (!_writeContext.inArray()) {
            _reportError("Current context not an ARRAY but "+_writeContext.getTypeDesc());
        }
        if (_cfgPrettyPrinter != null) {
            _cfgPrettyPrinter.writeEndArray(this, _writeContext.getEntryCount());
        } else {
            if (_outputTail >= _outputEnd) {
                _flushBuffer();
            }
            _outputBuffer[_outputTail++] = BYTE_RBRACKET;
        }
        _writeContext = _writeContext.clearAndGetParent();
    }

    @Override
    public final void writeStartObject() throws IOException
    {
        _verifyValueWrite("start an object");
        _writeContext = _writeContext.createChildObjectContext();
        if (_cfgPrettyPrinter != null) {
            _cfgPrettyPrinter.writeStartObject(this);
        } else {
            if (_outputTail >= _outputEnd) {
                _flushBuffer();
            }
            _outputBuffer[_outputTail++] = BYTE_LCURLY;
        }
    }

    @Override
    public final void writeEndObject() throws IOException
    {
        if (!_writeContext.inObject()) {
            _reportError("Current context not an object but "+_writeContext.getTypeDesc());
        }
        if (_cfgPrettyPrinter != null) {
            _cfgPrettyPrinter.writeEndObject(this, _writeContext.getEntryCount());
        } else {
            if (_outputTail >= _outputEnd) {
                _flushBuffer();
            }
            _outputBuffer[_outputTail++] = BYTE_RCURLY;
        }
        _writeContext = _writeContext.clearAndGetParent();
    }

    /**
     * Specialized version of <code>_writeFieldName</code>, off-lined
     * to keep the "fast path" as simple (and hopefully fast) as possible.
     */
    protected final void _writePPFieldName(String name) throws IOException
    {
        int status = _writeContext.writeFieldName(name);
        if (status == JsonWriteContext.STATUS_EXPECT_VALUE) {
            _reportError("Can not write a field name, expecting a value");
        }
        if ((status == JsonWriteContext.STATUS_OK_AFTER_COMMA)) {
            _cfgPrettyPrinter.writeObjectEntrySeparator(this);
        } else {
            _cfgPrettyPrinter.beforeObjectEntries(this);
        }
        if (_cfgUnqNames) {
            _writeStringSegments(name, false);
            return;
        }
        final int len = name.length();
        if (len > _charBufferLength) {
            _writeStringSegments(name, true);
            return;
        }
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
        name.getChars(0, len, _charBuffer, 0);
        // But as one segment, or multiple?
        if (len <= _outputMaxContiguous) {
            if ((_outputTail + len) > _outputEnd) { // caller must ensure enough space
                _flushBuffer();
            }
            _writeStringSegment(_charBuffer, 0, len);
        } else {
            _writeStringSegments(_charBuffer, 0, len);
        }
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
    }

    protected final void _writePPFieldName(SerializableString name) throws IOException
    {
        final int status = _writeContext.writeFieldName(name.getValue());
        if (status == JsonWriteContext.STATUS_EXPECT_VALUE) {
            _reportError("Can not write a field name, expecting a value");
        }
        if (status == JsonWriteContext.STATUS_OK_AFTER_COMMA) {
            _cfgPrettyPrinter.writeObjectEntrySeparator(this);
        } else {
            _cfgPrettyPrinter.beforeObjectEntries(this);
        }

        final boolean addQuotes = !_cfgUnqNames; // standard
        if (addQuotes) {
            if (_outputTail >= _outputEnd) {
                _flushBuffer();
            }
            _outputBuffer[_outputTail++] = BYTE_QUOTE;
        }
        _writeBytes(name.asQuotedUTF8());
        if (addQuotes) {
            if (_outputTail >= _outputEnd) {
                _flushBuffer();
            }
            _outputBuffer[_outputTail++] = BYTE_QUOTE;
        }
    }
    
    /*
    /**********************************************************
    /* Output method implementations, textual
    /**********************************************************
     */

    @Override
    public void writeString(String text) throws IOException
    {
        _verifyValueWrite(WRITE_STRING);
        if (text == null) {
            _writeNull();
            return;
        }
        // First: if we can't guarantee it all fits, quoted, within output, offline
        final int len = text.length();
        if (len > _outputMaxContiguous) { // nope: off-line handling
            _writeStringSegments(text, true);
            return;
        }
        if ((_outputTail + len) >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
        _writeStringSegment(text, 0, len); // we checked space already above
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
    }

    @Override
    public void writeString(char[] text, int offset, int len) throws IOException
    {
        _verifyValueWrite(WRITE_STRING);
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
        // One or multiple segments?
        if (len <= _outputMaxContiguous) {
            if ((_outputTail + len) > _outputEnd) { // caller must ensure enough space
                _flushBuffer();
            }
            _writeStringSegment(text, offset, len);
        } else {
            _writeStringSegments(text, offset, len);
        }
        // And finally, closing quotes
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
    }

    @Override
    public final void writeString(SerializableString text) throws IOException
    {
        _verifyValueWrite(WRITE_STRING);
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
        int len = text.appendQuotedUTF8(_outputBuffer, _outputTail);
        if (len < 0) {
            _writeBytes(text.asQuotedUTF8());
        } else {
            _outputTail += len;
        }
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
    }
    
    @Override
    public void writeRawUTF8String(byte[] text, int offset, int length) throws IOException
    {
        _verifyValueWrite(WRITE_STRING);
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
        _writeBytes(text, offset, length);
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
    }

    @Override
    public void writeUTF8String(byte[] text, int offset, int len) throws IOException
    {
        _verifyValueWrite(WRITE_STRING);
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
        // One or multiple segments?
        if (len <= _outputMaxContiguous) {
            _writeUTF8Segment(text, offset, len);
        } else {
            _writeUTF8Segments(text, offset, len);
        }
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
    }

    /*
    /**********************************************************
    /* Output method implementations, unprocessed ("raw")
    /**********************************************************
     */

    @Override
    public void writeRaw(String text) throws IOException {
        writeRaw(text, 0, text.length());
    }

    @Override
    public void writeRaw(String text, int offset, int len) throws IOException
    {
        final char[] buf = _charBuffer;

        // minor optimization: see if we can just get and copy

        // If not, need segmented approach. For speed, let's also use input buffer
        // size that is guaranteed to fit in output buffer; each char can expand to
        // at most 3 bytes, so at most 1/3 of buffer size.

        while (len > 0) {
            int len2 = Math.min(buf.length, len);
            text.getChars(offset, offset+len2, buf, 0);
            writeRaw(buf, 0, len2);
            // If this is NOT the last segment and if the last character looks like
            // split surrogate second half, drop it
            offset += len2;
            len -= len2;
        }
    }

    @Override
    public void writeRaw(SerializableString text) throws IOException
    {
        byte[] raw = text.asUnquotedUTF8();
        if (raw.length > 0) {
            _writeBytes(raw);
        }
    }

    // since 2.5
    @Override
    public void writeRawValue(SerializableString text) throws IOException {
        _verifyValueWrite(WRITE_RAW);
        byte[] raw = text.asUnquotedUTF8();
        if (raw.length > 0) {
            _writeBytes(raw);
        }
    }

    // @TODO: rewrite for speed...
    @Override
    public final void writeRaw(char[] cbuf, int offset, int len) throws IOException
    {
        // First: if we have 3 x charCount spaces, we know it'll fit just fine
        {
            int len3 = len+len+len;
            if ((_outputTail + len3) > _outputEnd) {
                // maybe we could flush?
                if (_outputEnd < len3) { // wouldn't be enough...
                    _writeSegmentedRaw(cbuf, offset, len);
                    return;
                }
                // yes, flushing brings enough space
                _flushBuffer();
            }
        }
        len += offset; // now marks the end

        // Note: here we know there is enough room, hence no output boundary checks
        main_loop:
        while (offset < len) {
            inner_loop:
            while (true) {
                int ch = (int) cbuf[offset];
                if (ch > 0x7F) {
                    break inner_loop;
                }
                _outputBuffer[_outputTail++] = (byte) ch;
                if (++offset >= len) {
                    break main_loop;
                }
            }
            char ch = cbuf[offset++];
            if (ch < 0x800) { // 2-byte?
                _outputBuffer[_outputTail++] = (byte) (0xc0 | (ch >> 6));
                _outputBuffer[_outputTail++] = (byte) (0x80 | (ch & 0x3f));
            } else {
                offset = _outputRawMultiByteChar(ch, cbuf, offset, len);
            }
        }
    }

    @Override
    public void writeRaw(char ch) throws IOException
    {
        if ((_outputTail + 3) >= _outputEnd) {
            _flushBuffer();
        }
        final byte[] bbuf = _outputBuffer;
        if (ch <= 0x7F) {
            bbuf[_outputTail++] = (byte) ch;
        } else  if (ch < 0x800) { // 2-byte?
            bbuf[_outputTail++] = (byte) (0xc0 | (ch >> 6));
            bbuf[_outputTail++] = (byte) (0x80 | (ch & 0x3f));
        } else {
            /*offset =*/ _outputRawMultiByteChar(ch, null, 0, 0);
        }
    }

    /**
     * Helper method called when it is possible that output of raw section
     * to output may cross buffer boundary
     */
    private final void _writeSegmentedRaw(char[] cbuf, int offset, int len) throws IOException
    {
        final int end = _outputEnd;
        final byte[] bbuf = _outputBuffer;
        final int inputEnd = offset + len;
        
        main_loop:
        while (offset < inputEnd) {
            inner_loop:
            while (true) {
                int ch = (int) cbuf[offset];
                if (ch >= 0x80) {
                    break inner_loop;
                }
                // !!! TODO: fast(er) writes (roll input, output checks in one)
                if (_outputTail >= end) {
                    _flushBuffer();
                }
                bbuf[_outputTail++] = (byte) ch;
                if (++offset >= inputEnd) {
                    break main_loop;
                }
            }
            if ((_outputTail + 3) >= _outputEnd) {
                _flushBuffer();
            }
            char ch = cbuf[offset++];
            if (ch < 0x800) { // 2-byte?
                bbuf[_outputTail++] = (byte) (0xc0 | (ch >> 6));
                bbuf[_outputTail++] = (byte) (0x80 | (ch & 0x3f));
            } else {
                offset = _outputRawMultiByteChar(ch, cbuf, offset, inputEnd);
            }
        }
    }

    /**
     * Helper method that is called for segmented write of raw content
     * when explicitly outputting a segment of longer thing.
     * Caller has to take care of ensuring there's no split surrogate
     * pair at the end (that is, last char can not be first part of a
     * surrogate char pair).
     *
     * @since 2.8.2
     */

    /*
    /**********************************************************
    /* Output method implementations, base64-encoded binary
    /**********************************************************
     */

    @Override
    public void writeBinary(Base64Variant b64variant,
            byte[] data, int offset, int len)
        throws IOException, JsonGenerationException
    {
        _verifyValueWrite(WRITE_BINARY);
        // Starting quotes
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
        _writeBinary(b64variant, data, offset, offset+len);
        // and closing quotes
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
    }

    @Override
    public int writeBinary(Base64Variant b64variant,
            InputStream data, int dataLength)
        throws IOException, JsonGenerationException
    {
        _verifyValueWrite(WRITE_BINARY);
        // Starting quotes
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
        byte[] encodingBuffer = _ioContext.allocBase64Buffer();
        int bytes;
        try {
            if (dataLength < 0) { // length unknown
                bytes = _writeBinary(b64variant, data, encodingBuffer);
            } else {
                int missing = _writeBinary(b64variant, data, encodingBuffer, dataLength);
                if (missing > 0) {
                    _reportError("Too few bytes available: missing "+missing+" bytes (out of "+dataLength+")");
                }
                bytes = dataLength;
            }
        } finally {
            _ioContext.releaseBase64Buffer(encodingBuffer);
        }
        // and closing quotes
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
        return bytes;
    }
    
    /*
    /**********************************************************
    /* Output method implementations, primitive
    /**********************************************************
     */

    @Override
    public void writeNumber(short s) throws IOException
    {
        _verifyValueWrite(WRITE_NUMBER);
        // up to 5 digits and possible minus sign
        if ((_outputTail + 6) >= _outputEnd) {
            _flushBuffer();
        }
        if (_cfgNumbersAsStrings) {
            _writeQuotedShort(s);
            return;
        }
        _outputTail = NumberOutput.outputInt(s, _outputBuffer, _outputTail);
    }
    
    private final void _writeQuotedShort(short s) throws IOException {
        if ((_outputTail + 8) >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
        _outputTail = NumberOutput.outputInt(s, _outputBuffer, _outputTail);
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
    } 
    
    @Override
    public void writeNumber(int i) throws IOException
    {
        _verifyValueWrite(WRITE_NUMBER);
        // up to 10 digits and possible minus sign
        if ((_outputTail + 11) >= _outputEnd) {
            _flushBuffer();
        }
        if (_cfgNumbersAsStrings) {
            _writeQuotedInt(i);
            return;
        }
        _outputTail = NumberOutput.outputInt(i, _outputBuffer, _outputTail);
    }

    private final void _writeQuotedInt(int i) throws IOException
    {
        if ((_outputTail + 13) >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
        _outputTail = NumberOutput.outputInt(i, _outputBuffer, _outputTail);
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
    }    

    @Override
    public void writeNumber(long l) throws IOException
    {
        _verifyValueWrite(WRITE_NUMBER);
        if (_cfgNumbersAsStrings) {
            _writeQuotedLong(l);
            return;
        }
        if ((_outputTail + 21) >= _outputEnd) {
            // up to 20 digits, minus sign
            _flushBuffer();
        }
        _outputTail = NumberOutput.outputLong(l, _outputBuffer, _outputTail);
    }

    private final void _writeQuotedLong(long l) throws IOException
    {
        if ((_outputTail + 23) >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
        _outputTail = NumberOutput.outputLong(l, _outputBuffer, _outputTail);
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
    }

    @Override
    public void writeNumber(BigInteger value) throws IOException
    {
        _verifyValueWrite(WRITE_NUMBER);
        if (value == null) {
            _writeNull();
        } else if (_cfgNumbersAsStrings) {
            _writeQuotedRaw(value.toString());
        } else {
            writeRaw(value.toString());
        }
    }

    
    @Override
    public void writeNumber(double d) throws IOException
    {
        if (_cfgNumbersAsStrings ||
            (((Double.isNaN(d) || Double.isInfinite(d))
                && Feature.QUOTE_NON_NUMERIC_NUMBERS.enabledIn(_features)))) {
            writeString(String.valueOf(d));
            return;
        }
        // What is the max length for doubles? 40 chars?
        _verifyValueWrite(WRITE_NUMBER);
        writeRaw(String.valueOf(d));
    }

    @Override
    public void writeNumber(float f) throws IOException
    {
        if (_cfgNumbersAsStrings ||
            // [JACKSON-139]
            (((Float.isNaN(f) || Float.isInfinite(f))
                && Feature.QUOTE_NON_NUMERIC_NUMBERS.enabledIn(_features)))) {
            writeString(String.valueOf(f));
            return;
        }
        // What is the max length for floats?
        _verifyValueWrite(WRITE_NUMBER);
        writeRaw(String.valueOf(f));
    }

    @Override
    public void writeNumber(BigDecimal value) throws IOException
    {
        // Don't really know max length for big decimal, no point checking
        _verifyValueWrite(WRITE_NUMBER);
        if (value == null) {
            _writeNull();
        } else if (_cfgNumbersAsStrings) {
            String raw = Feature.WRITE_BIGDECIMAL_AS_PLAIN.enabledIn(_features)
                    ? value.toPlainString() : value.toString();
            _writeQuotedRaw(raw);
        } else if (Feature.WRITE_BIGDECIMAL_AS_PLAIN.enabledIn(_features)) {
            writeRaw(value.toPlainString());
        } else {
            writeRaw(value.toString());
        }
    }

    @Override
    public void writeNumber(String encodedValue) throws IOException
    {
        _verifyValueWrite(WRITE_NUMBER);
        if (_cfgNumbersAsStrings) {
            _writeQuotedRaw(encodedValue);            
        } else {
            writeRaw(encodedValue);
        }
    }

    private final void _writeQuotedRaw(String value) throws IOException
    {
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
        writeRaw(value);
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = BYTE_QUOTE;
    }
    
    @Override
    public void writeBoolean(boolean state) throws IOException
    {
        _verifyValueWrite(WRITE_BOOLEAN);
        if ((_outputTail + 5) >= _outputEnd) {
            _flushBuffer();
        }
        byte[] keyword = state ? TRUE_BYTES : FALSE_BYTES;
        int len = keyword.length;
        System.arraycopy(keyword, 0, _outputBuffer, _outputTail, len);
        _outputTail += len;
    }

    @Override
    public void writeNull() throws IOException
    {
        _verifyValueWrite(WRITE_NULL);
        _writeNull();
    }

    /*
    /**********************************************************
    /* Implementations for other methods
    /**********************************************************
     */

    @Override
    protected final void _verifyValueWrite(String typeMsg) throws IOException
    {
        int status = _writeContext.writeValue();
        if (status == JsonWriteContext.STATUS_EXPECT_NAME) {
            _reportError("Can not "+typeMsg+", expecting field name");
        }
        if (_cfgPrettyPrinter == null) {
            byte b;
            switch (status) {
            case JsonWriteContext.STATUS_OK_AFTER_COMMA:
                b = BYTE_COMMA;
                break;
            case JsonWriteContext.STATUS_OK_AFTER_COLON:
                b = BYTE_COLON;
                break;
            case JsonWriteContext.STATUS_OK_AFTER_SPACE: // root-value separator
                if (_rootValueSeparator != null) {
                    byte[] raw = _rootValueSeparator.asUnquotedUTF8();
                    if (raw.length > 0) {
                        _writeBytes(raw);
                    }
                }
                return;
            case JsonWriteContext.STATUS_OK_AS_IS:
            default:
                return;
            }
            if (_outputTail >= _outputEnd) {
                _flushBuffer();
            }
            _outputBuffer[_outputTail] = b;
            ++_outputTail;
            return;
        }
        // Otherwise, pretty printer knows what to do...
        _verifyPrettyValueWrite(typeMsg, status);
    }

    protected final void _verifyPrettyValueWrite(String typeMsg, int status) throws IOException
    {
        // If we have a pretty printer, it knows what to do:
        switch (status) {
        case JsonWriteContext.STATUS_OK_AFTER_COMMA: // array
            _cfgPrettyPrinter.writeArrayValueSeparator(this);
            break;
        case JsonWriteContext.STATUS_OK_AFTER_COLON:
            _cfgPrettyPrinter.writeObjectFieldValueSeparator(this);
            break;
        case JsonWriteContext.STATUS_OK_AFTER_SPACE:
            _cfgPrettyPrinter.writeRootValueSeparator(this);
            break;
        case JsonWriteContext.STATUS_OK_AS_IS:
            // First entry, but of which context?
            if (_writeContext.inArray()) {
                _cfgPrettyPrinter.beforeArrayValues(this);
            } else if (_writeContext.inObject()) {
                _cfgPrettyPrinter.beforeObjectEntries(this);
            }
            break;
        default:
            _throwInternal();
            break;
        }
    }

    /*
    /**********************************************************
    /* Low-level output handling
    /**********************************************************
     */

    @Override
    public void flush() throws IOException
    {
        _flushBuffer();
        if (_outputStream != null) {
            if (isEnabled(Feature.FLUSH_PASSED_TO_STREAM)) {
                _outputStream.flush();
            }
        }
    }

    @Override
    public void close() throws IOException
    {
        super.close();

        /* 05-Dec-2008, tatu: To add [JACKSON-27], need to close open
         *   scopes.
         */
        // First: let's see that we still have buffers...
        if ((_outputBuffer != null)
            && isEnabled(Feature.AUTO_CLOSE_JSON_CONTENT)) {
            while (true) {
                JsonStreamContext ctxt = getOutputContext();
                if (ctxt.inArray()) {
                    writeEndArray();
                } else if (ctxt.inObject()) {
                    writeEndObject();
                } else {
                    break;
                }
            }
        }
        _flushBuffer();
        _outputTail = 0; // just to ensure we don't think there's anything buffered

        /* 25-Nov-2008, tatus: As per [JACKSON-16] we are not to call close()
         *   on the underlying Reader, unless we "own" it, or auto-closing
         *   feature is enabled.
         *   One downside: when using UTF8Writer, underlying buffer(s)
         *   may not be properly recycled if we don't close the writer.
         */
        if (_outputStream != null) {
            if (_ioContext.isResourceManaged() || isEnabled(Feature.AUTO_CLOSE_TARGET)) {
                _outputStream.close();
            } else if (isEnabled(Feature.FLUSH_PASSED_TO_STREAM)) {
                // If we can't close it, we should at least flush
                _outputStream.flush();
            }
        }
        // Internal buffer(s) generator has can now be released as well
        _releaseBuffers();
    }

    @Override
    protected void _releaseBuffers()
    {
        byte[] buf = _outputBuffer;
        if (buf != null && _bufferRecyclable) {
            _outputBuffer = null;
            _ioContext.releaseWriteEncodingBuffer(buf);
        }
        char[] cbuf = _charBuffer;
        if (cbuf != null) {
            _charBuffer = null;
            _ioContext.releaseConcatBuffer(cbuf);
        }
    }

    /*
    /**********************************************************
    /* Internal methods, low-level writing, raw bytes
    /**********************************************************
     */

    private final void _writeBytes(byte[] bytes) throws IOException
    {
        final int len = bytes.length;
        if ((_outputTail + len) > _outputEnd) {
            _flushBuffer();
            // still not enough?
            if (len > MAX_BYTES_TO_BUFFER) {
                _outputStream.write(bytes, 0, len);
                return;
            }
        }
        System.arraycopy(bytes, 0, _outputBuffer, _outputTail, len);
        _outputTail += len;
    }

    private final void _writeBytes(byte[] bytes, int offset, int len) throws IOException
    {
        if ((_outputTail + len) > _outputEnd) {
            _flushBuffer();
            // still not enough?
            if (len > MAX_BYTES_TO_BUFFER) {
                _outputStream.write(bytes, offset, len);
                return;
            }
        }
        System.arraycopy(bytes, offset, _outputBuffer, _outputTail, len);
        _outputTail += len;
    }

    /*
    /**********************************************************
    /* Internal methods, mid-level writing, String segments
    /**********************************************************
     */
    
    /**
     * Method called when String to write is long enough not to fit
     * completely in temporary copy buffer. If so, we will actually
     * copy it in small enough chunks so it can be directly fed
     * to single-segment writes (instead of maximum slices that
     * would fit in copy buffer)
     */
    private final void _writeStringSegments(String text, boolean addQuotes) throws IOException
    {
        if (addQuotes) {
            if (_outputTail >= _outputEnd) {
                _flushBuffer();
            }
            _outputBuffer[_outputTail++] = BYTE_QUOTE;        
        }

        int left = text.length();
        int offset = 0;

        while (left > 0) {
            int len = Math.min(_outputMaxContiguous, left);
            if ((_outputTail + len) > _outputEnd) { // caller must ensure enough space
                _flushBuffer();
            }
            _writeStringSegment(text, offset, len);
            offset += len;
            left -= len;
        }

        if (addQuotes) {
            if (_outputTail >= _outputEnd) {
                _flushBuffer();
            }
            _outputBuffer[_outputTail++] = BYTE_QUOTE;
        }
    }

    /**
     * Method called when character sequence to write is long enough that
     * its maximum encoded and escaped form is not guaranteed to fit in
     * the output buffer. If so, we will need to choose smaller output
     * chunks to write at a time.
     */
    private final void _writeStringSegments(char[] cbuf, int offset, int totalLen) throws IOException
    {
        do {
            int len = Math.min(_outputMaxContiguous, totalLen);
            if ((_outputTail + len) > _outputEnd) { // caller must ensure enough space
                _flushBuffer();
            }
            _writeStringSegment(cbuf, offset, len);
            offset += len;
            totalLen -= len;
        } while (totalLen > 0);
    }

    private final void _writeStringSegments(String text, int offset, int totalLen) throws IOException
    {
        do {
            int len = Math.min(_outputMaxContiguous, totalLen);
            if ((_outputTail + len) > _outputEnd) { // caller must ensure enough space
                _flushBuffer();
            }
            _writeStringSegment(text, offset, len);
            offset += len;
            totalLen -= len;
        } while (totalLen > 0);
    }

    /*
    /**********************************************************
    /* Internal methods, low-level writing, text segments
    /**********************************************************
     */

    /**
     * This method called when the string content is already in
     * a char buffer, and its maximum total encoded and escaped length
     * can not exceed size of the output buffer.
     * Caller must ensure that there is enough space in output buffer,
     * assuming case of all non-escaped ASCII characters, as well as
     * potentially enough space for other cases (but not necessarily flushed)
     */
    private final void _writeStringSegment(char[] cbuf, int offset, int len)
        throws IOException
    {
        // note: caller MUST ensure (via flushing) there's room for ASCII only
        
        // Fast+tight loop for ASCII-only, no-escaping-needed output
        len += offset; // becomes end marker, then

        int outputPtr = _outputTail;
        final byte[] outputBuffer = _outputBuffer;
        final int[] escCodes = _outputEscapes;

        while (offset < len) {
            int ch = cbuf[offset];
            // note: here we know that (ch > 0x7F) will cover case of escaping non-ASCII too:
            if (ch > 0x7F || escCodes[ch] != 0) {
                break;
            }
            outputBuffer[outputPtr++] = (byte) ch;
            ++offset;
        }
        _outputTail = outputPtr;
        if (offset < len) {
            // [JACKSON-106]
            if (_characterEscapes != null) {
                _writeCustomStringSegment2(cbuf, offset, len);
            // [JACKSON-102]
            } else if (_maximumNonEscapedChar == 0) {
                _writeStringSegment2(cbuf, offset, len);
            } else {
                _writeStringSegmentASCII2(cbuf, offset, len);
            }

        }
    }

    private final void _writeStringSegment(String text, int offset, int len) throws IOException
    {
        // note: caller MUST ensure (via flushing) there's room for ASCII only
        // Fast+tight loop for ASCII-only, no-escaping-needed output
        len += offset; // becomes end marker, then

        int outputPtr = _outputTail;
        final byte[] outputBuffer = _outputBuffer;
        final int[] escCodes = _outputEscapes;

        while (offset < len) {
            int ch = text.charAt(offset);
            // note: here we know that (ch > 0x7F) will cover case of escaping non-ASCII too:
            if (ch > 0x7F || escCodes[ch] != 0) {
                break;
            }
            outputBuffer[outputPtr++] = (byte) ch;
            ++offset;
        }
        _outputTail = outputPtr;
        if (offset < len) {
            if (_characterEscapes != null) {
                _writeCustomStringSegment2(text, offset, len);
            } else if (_maximumNonEscapedChar == 0) {
                _writeStringSegment2(text, offset, len);
            } else {
                _writeStringSegmentASCII2(text, offset, len);
            }
        }
    }

    /**
     * Secondary method called when content contains characters to escape,
     * and/or multi-byte UTF-8 characters.
     */
    private final void _writeStringSegment2(final char[] cbuf, int offset, final int end) throws IOException
    {
        // Ok: caller guarantees buffer can have room; but that may require flushing:
        if ((_outputTail +  6 * (end - offset)) > _outputEnd) {
            _flushBuffer();
        }

        int outputPtr = _outputTail;

        final byte[] outputBuffer = _outputBuffer;
        final int[] escCodes = _outputEscapes;
        
        while (offset < end) {
            int ch = cbuf[offset++];
            if (ch <= 0x7F) {
                 if (escCodes[ch] == 0) {
                     outputBuffer[outputPtr++] = (byte) ch;
                     continue;
                 }
                 int escape = escCodes[ch];
                 if (escape > 0) { // 2-char escape, fine
                     outputBuffer[outputPtr++] = BYTE_BACKSLASH;
                     outputBuffer[outputPtr++] = (byte) escape;
                 } else {
                     // ctrl-char, 6-byte escape...
                     outputPtr = _writeGenericEscape(ch, outputPtr);
                }
                continue;
            }
            if (ch <= 0x7FF) { // fine, just needs 2 byte output
                outputBuffer[outputPtr++] = (byte) (0xc0 | (ch >> 6));
                outputBuffer[outputPtr++] = (byte) (0x80 | (ch & 0x3f));
            } else {
                outputPtr = _outputMultiByteChar(ch, outputPtr);
            }
        }
        _outputTail = outputPtr;
    }

    private final void _writeStringSegment2(final String text, int offset, final int end) throws IOException
    {
        if ((_outputTail +  6 * (end - offset)) > _outputEnd) {
            _flushBuffer();
        }

        int outputPtr = _outputTail;

        final byte[] outputBuffer = _outputBuffer;
        final int[] escCodes = _outputEscapes;
        
        while (offset < end) {
            int ch = text.charAt(offset++);
            if (ch <= 0x7F) {
                 if (escCodes[ch] == 0) {
                     outputBuffer[outputPtr++] = (byte) ch;
                     continue;
                 }
                 int escape = escCodes[ch];
                 if (escape > 0) { // 2-char escape, fine
                     outputBuffer[outputPtr++] = BYTE_BACKSLASH;
                     outputBuffer[outputPtr++] = (byte) escape;
                 } else {
                     // ctrl-char, 6-byte escape...
                     outputPtr = _writeGenericEscape(ch, outputPtr);
                }
                continue;
            }
            if (ch <= 0x7FF) { // fine, just needs 2 byte output
                outputBuffer[outputPtr++] = (byte) (0xc0 | (ch >> 6));
                outputBuffer[outputPtr++] = (byte) (0x80 | (ch & 0x3f));
            } else {
                outputPtr = _outputMultiByteChar(ch, outputPtr);
            }
        }
        _outputTail = outputPtr;
    }
    
    /*
    /**********************************************************
    /* Internal methods, low-level writing, text segment
    /* with additional escaping (ASCII or such)
    /**********************************************************
     */

    /**
     * Same as <code>_writeStringSegment2(char[], ...)</code., but with
     * additional escaping for high-range code points
     */
    private final void _writeStringSegmentASCII2(final char[] cbuf, int offset, final int end) throws IOException
    {
        // Ok: caller guarantees buffer can have room; but that may require flushing:
        if ((_outputTail +  6 * (end - offset)) > _outputEnd) {
            _flushBuffer();
        }
    
        int outputPtr = _outputTail;
    
        final byte[] outputBuffer = _outputBuffer;
        final int[] escCodes = _outputEscapes;
        final int maxUnescaped = _maximumNonEscapedChar;
        
        while (offset < end) {
            int ch = cbuf[offset++];
            if (ch <= 0x7F) {
                 if (escCodes[ch] == 0) {
                     outputBuffer[outputPtr++] = (byte) ch;
                     continue;
                 }
                 int escape = escCodes[ch];
                 if (escape > 0) { // 2-char escape, fine
                     outputBuffer[outputPtr++] = BYTE_BACKSLASH;
                     outputBuffer[outputPtr++] = (byte) escape;
                 } else {
                     // ctrl-char, 6-byte escape...
                     outputPtr = _writeGenericEscape(ch, outputPtr);
                 }
                 continue;
            }
            if (ch > maxUnescaped) { // [JACKSON-102] Allow forced escaping if non-ASCII (etc) chars:
                outputPtr = _writeGenericEscape(ch, outputPtr);
                continue;
            }
            if (ch <= 0x7FF) { // fine, just needs 2 byte output
                outputBuffer[outputPtr++] = (byte) (0xc0 | (ch >> 6));
                outputBuffer[outputPtr++] = (byte) (0x80 | (ch & 0x3f));
            } else {
                outputPtr = _outputMultiByteChar(ch, outputPtr);
            }
        }
        _outputTail = outputPtr;
    }

    private final void _writeStringSegmentASCII2(final String text, int offset, final int end) throws IOException
    {
        // Ok: caller guarantees buffer can have room; but that may require flushing:
        if ((_outputTail +  6 * (end - offset)) > _outputEnd) {
            _flushBuffer();
        }
    
        int outputPtr = _outputTail;
    
        final byte[] outputBuffer = _outputBuffer;
        final int[] escCodes = _outputEscapes;
        final int maxUnescaped = _maximumNonEscapedChar;
        
        while (offset < end) {
            int ch = text.charAt(offset++);
            if (ch <= 0x7F) {
                 if (escCodes[ch] == 0) {
                     outputBuffer[outputPtr++] = (byte) ch;
                     continue;
                 }
                 int escape = escCodes[ch];
                 if (escape > 0) { // 2-char escape, fine
                     outputBuffer[outputPtr++] = BYTE_BACKSLASH;
                     outputBuffer[outputPtr++] = (byte) escape;
                 } else {
                     // ctrl-char, 6-byte escape...
                     outputPtr = _writeGenericEscape(ch, outputPtr);
                 }
                 continue;
            }
            if (ch > maxUnescaped) { // [JACKSON-102] Allow forced escaping if non-ASCII (etc) chars:
                outputPtr = _writeGenericEscape(ch, outputPtr);
                continue;
            }
            if (ch <= 0x7FF) { // fine, just needs 2 byte output
                outputBuffer[outputPtr++] = (byte) (0xc0 | (ch >> 6));
                outputBuffer[outputPtr++] = (byte) (0x80 | (ch & 0x3f));
            } else {
                outputPtr = _outputMultiByteChar(ch, outputPtr);
            }
        }
        _outputTail = outputPtr;
    }
    
    /*
    /**********************************************************
    /* Internal methods, low-level writing, text segment
    /* with fully custom escaping (and possibly escaping of non-ASCII
    /**********************************************************
     */

    /**
     * Same as <code>_writeStringSegmentASCII2(char[], ...)</code., but with
     * additional checking for completely custom escapes
     */
    private final void _writeCustomStringSegment2(final char[] cbuf, int offset, final int end) throws IOException
    {
        // Ok: caller guarantees buffer can have room; but that may require flushing:
        if ((_outputTail +  6 * (end - offset)) > _outputEnd) {
            _flushBuffer();
        }
        int outputPtr = _outputTail;
    
        final byte[] outputBuffer = _outputBuffer;
        final int[] escCodes = _outputEscapes;
        // may or may not have this limit
        final int maxUnescaped = (_maximumNonEscapedChar <= 0) ? 0xFFFF : _maximumNonEscapedChar;
        final CharacterEscapes customEscapes = _characterEscapes; // non-null
        
        while (offset < end) {
            int ch = cbuf[offset++];
            if (ch <= 0x7F) {
                 if (escCodes[ch] == 0) {
                     outputBuffer[outputPtr++] = (byte) ch;
                     continue;
                 }
                 int escape = escCodes[ch];
                 if (escape > 0) { // 2-char escape, fine
                     outputBuffer[outputPtr++] = BYTE_BACKSLASH;
                     outputBuffer[outputPtr++] = (byte) escape;
                 } else if (escape == CharacterEscapes.ESCAPE_CUSTOM) {
                     SerializableString esc = customEscapes.getEscapeSequence(ch);
                     if (esc == null) {
                         _reportError("Invalid custom escape definitions; custom escape not found for character code 0x"
                                 +Integer.toHexString(ch)+", although was supposed to have one");
                     }
                     outputPtr = _writeCustomEscape(outputBuffer, outputPtr, esc, end-offset);
                 } else {
                     // ctrl-char, 6-byte escape...
                     outputPtr = _writeGenericEscape(ch, outputPtr);
                 }
                 continue;
            }
            if (ch > maxUnescaped) { // [JACKSON-102] Allow forced escaping if non-ASCII (etc) chars:
                outputPtr = _writeGenericEscape(ch, outputPtr);
                continue;
            }
            SerializableString esc = customEscapes.getEscapeSequence(ch);
            if (esc != null) {
                outputPtr = _writeCustomEscape(outputBuffer, outputPtr, esc, end-offset);
                continue;
            }
            if (ch <= 0x7FF) { // fine, just needs 2 byte output
                outputBuffer[outputPtr++] = (byte) (0xc0 | (ch >> 6));
                outputBuffer[outputPtr++] = (byte) (0x80 | (ch & 0x3f));
            } else {
                outputPtr = _outputMultiByteChar(ch, outputPtr);
            }
        }
        _outputTail = outputPtr;
    }

    private final void _writeCustomStringSegment2(final String text, int offset, final int end) throws IOException
    {
        // Ok: caller guarantees buffer can have room; but that may require flushing:
        if ((_outputTail +  6 * (end - offset)) > _outputEnd) {
            _flushBuffer();
        }
        int outputPtr = _outputTail;
    
        final byte[] outputBuffer = _outputBuffer;
        final int[] escCodes = _outputEscapes;
        // may or may not have this limit
        final int maxUnescaped = (_maximumNonEscapedChar <= 0) ? 0xFFFF : _maximumNonEscapedChar;
        final CharacterEscapes customEscapes = _characterEscapes; // non-null
        
        while (offset < end) {
            int ch = text.charAt(offset++);
            if (ch <= 0x7F) {
                 if (escCodes[ch] == 0) {
                     outputBuffer[outputPtr++] = (byte) ch;
                     continue;
                 }
                 int escape = escCodes[ch];
                 if (escape > 0) { // 2-char escape, fine
                     outputBuffer[outputPtr++] = BYTE_BACKSLASH;
                     outputBuffer[outputPtr++] = (byte) escape;
                 } else if (escape == CharacterEscapes.ESCAPE_CUSTOM) {
                     SerializableString esc = customEscapes.getEscapeSequence(ch);
                     if (esc == null) {
                         _reportError("Invalid custom escape definitions; custom escape not found for character code 0x"
                                 +Integer.toHexString(ch)+", although was supposed to have one");
                     }
                     outputPtr = _writeCustomEscape(outputBuffer, outputPtr, esc, end-offset);
                 } else {
                     // ctrl-char, 6-byte escape...
                     outputPtr = _writeGenericEscape(ch, outputPtr);
                 }
                 continue;
            }
            if (ch > maxUnescaped) { // [JACKSON-102] Allow forced escaping if non-ASCII (etc) chars:
                outputPtr = _writeGenericEscape(ch, outputPtr);
                continue;
            }
            SerializableString esc = customEscapes.getEscapeSequence(ch);
            if (esc != null) {
                outputPtr = _writeCustomEscape(outputBuffer, outputPtr, esc, end-offset);
                continue;
            }
            if (ch <= 0x7FF) { // fine, just needs 2 byte output
                outputBuffer[outputPtr++] = (byte) (0xc0 | (ch >> 6));
                outputBuffer[outputPtr++] = (byte) (0x80 | (ch & 0x3f));
            } else {
                outputPtr = _outputMultiByteChar(ch, outputPtr);
            }
        }
        _outputTail = outputPtr;
    }

    private final int _writeCustomEscape(byte[] outputBuffer, int outputPtr, SerializableString esc, int remainingChars)
        throws IOException, JsonGenerationException
    {
        byte[] raw = esc.asUnquotedUTF8(); // must be escaped at this point, shouldn't double-quote
        int len = raw.length;
        if (len > 6) { // may violate constraints we have, do offline
            return _handleLongCustomEscape(outputBuffer, outputPtr, _outputEnd, raw, remainingChars);
        }
        // otherwise will fit without issues, so:
        System.arraycopy(raw, 0, outputBuffer, outputPtr, len);
        return (outputPtr + len);
    }
    
    private final int _handleLongCustomEscape(byte[] outputBuffer, int outputPtr, int outputEnd, byte[] raw,
            int remainingChars)
        throws IOException, JsonGenerationException
    {
        int len = raw.length;
        if ((outputPtr + len) > outputEnd) {
            _outputTail = outputPtr;
            _flushBuffer();
            outputPtr = _outputTail;
            if (len > outputBuffer.length) { // very unlikely, but possible...
                _outputStream.write(raw, 0, len);
                return outputPtr;
            }
            System.arraycopy(raw, 0, outputBuffer, outputPtr, len);
            outputPtr += len;
        }
        // but is the invariant still obeyed? If not, flush once more
        if ((outputPtr +  6 * remainingChars) > outputEnd) {
            _flushBuffer();
            return _outputTail;
        }
        return outputPtr;
    }

    /*
    /**********************************************************
    /* Internal methods, low-level writing, "raw UTF-8" segments
    /**********************************************************
     */
    
    /**
     * Method called when UTF-8 encoded (but NOT yet escaped!) content is not guaranteed
     * to fit in the output buffer after escaping; as such, we just need to
     * chunk writes.
     */
    private final void _writeUTF8Segments(byte[] utf8, int offset, int totalLen)
        throws IOException, JsonGenerationException
    {
        do {
            int len = Math.min(_outputMaxContiguous, totalLen);
            _writeUTF8Segment(utf8, offset, len);
            offset += len;
            totalLen -= len;
        } while (totalLen > 0);
    }
    
    private final void _writeUTF8Segment(byte[] utf8, final int offset, final int len)
        throws IOException, JsonGenerationException
    {
        // fast loop to see if escaping is needed; don't copy, just look
        final int[] escCodes = _outputEscapes;

        for (int ptr = offset, end = offset + len; ptr < end; ) {
            // 28-Feb-2011, tatu: escape codes just cover 7-bit range, so:
            int ch = utf8[ptr++];
            if ((ch >= 0) && escCodes[ch] != 0) {
                _writeUTF8Segment2(utf8, offset, len);
                return;
            }
        }
        
        // yes, fine, just copy the sucker
        if ((_outputTail + len) > _outputEnd) { // enough room or need to flush?
            _flushBuffer(); // but yes once we flush (caller guarantees length restriction)
        }
        System.arraycopy(utf8, offset, _outputBuffer, _outputTail, len);
        _outputTail += len;
    }

    private final void _writeUTF8Segment2(final byte[] utf8, int offset, int len)
        throws IOException, JsonGenerationException
    {
        int outputPtr = _outputTail;

        // Ok: caller guarantees buffer can have room; but that may require flushing:
        if ((outputPtr + (len * 6)) > _outputEnd) {
            _flushBuffer();
            outputPtr = _outputTail;
        }
        
        final byte[] outputBuffer = _outputBuffer;
        final int[] escCodes = _outputEscapes;
        len += offset; // so 'len' becomes 'end'
        
        while (offset < len) {
            byte b = utf8[offset++];
            int ch = b;
            if (ch < 0 || escCodes[ch] == 0) {
                outputBuffer[outputPtr++] = b;
                continue;
            }
            int escape = escCodes[ch];
            if (escape > 0) { // 2-char escape, fine
                outputBuffer[outputPtr++] = BYTE_BACKSLASH;
                outputBuffer[outputPtr++] = (byte) escape;
            } else {
                // ctrl-char, 6-byte escape...
                outputPtr = _writeGenericEscape(ch, outputPtr);
            }
        }
        _outputTail = outputPtr;
    }
    
    /*
    /**********************************************************
    /* Internal methods, low-level writing, base64 encoded
    /**********************************************************
     */
    
    protected final void _writeBinary(Base64Variant b64variant,
            byte[] input, int inputPtr, final int inputEnd)
        throws IOException, JsonGenerationException
    {
        // Encoding is by chunks of 3 input, 4 output chars, so:
        int safeInputEnd = inputEnd - 3;
        // Let's also reserve room for possible (and quoted) lf char each round
        int safeOutputEnd = _outputEnd - 6;
        int chunksBeforeLF = b64variant.getMaxLineLength() >> 2;

        // Ok, first we loop through all full triplets of data:
        while (inputPtr <= safeInputEnd) {
            if (_outputTail > safeOutputEnd) { // need to flush
                _flushBuffer();
            }
            // First, mash 3 bytes into lsb of 32-bit int
            int b24 = ((int) input[inputPtr++]) << 8;
            b24 |= ((int) input[inputPtr++]) & 0xFF;
            b24 = (b24 << 8) | (((int) input[inputPtr++]) & 0xFF);
            _outputTail = b64variant.encodeBase64Chunk(b24, _outputBuffer, _outputTail);
            if (--chunksBeforeLF <= 0) {
                // note: must quote in JSON value
                _outputBuffer[_outputTail++] = '\\';
                _outputBuffer[_outputTail++] = 'n';
                chunksBeforeLF = b64variant.getMaxLineLength() >> 2;
            }
        }

        // And then we may have 1 or 2 leftover bytes to encode
        int inputLeft = inputEnd - inputPtr; // 0, 1 or 2
        if (inputLeft > 0) { // yes, but do we have room for output?
            if (_outputTail > safeOutputEnd) { // don't really need 6 bytes but...
                _flushBuffer();
            }
            int b24 = ((int) input[inputPtr++]) << 16;
            if (inputLeft == 2) {
                b24 |= (((int) input[inputPtr++]) & 0xFF) << 8;
            }
            _outputTail = b64variant.encodeBase64Partial(b24, inputLeft, _outputBuffer, _outputTail);
        }
    }

    // write-method called when length is definitely known
    protected final int _writeBinary(Base64Variant b64variant,
            InputStream data, byte[] readBuffer, int bytesLeft)
        throws IOException, JsonGenerationException
    {
        int inputPtr = 0;
        int inputEnd = 0;
        int lastFullOffset = -3;       
        
        // Let's also reserve room for possible (and quoted) LF char each round
        int safeOutputEnd = _outputEnd - 6;
        int chunksBeforeLF = b64variant.getMaxLineLength() >> 2;

        while (bytesLeft > 2) { // main loop for full triplets
            if (inputPtr > lastFullOffset) {
                inputEnd = _readMore(data, readBuffer, inputPtr, inputEnd, bytesLeft);
                inputPtr = 0;
                if (inputEnd < 3) { // required to try to read to have at least 3 bytes
                    break;
                }
                lastFullOffset = inputEnd-3;
            }
            if (_outputTail > safeOutputEnd) { // need to flush
                _flushBuffer();
            }
            int b24 = ((int) readBuffer[inputPtr++]) << 8;
            b24 |= ((int) readBuffer[inputPtr++]) & 0xFF;
            b24 = (b24 << 8) | (((int) readBuffer[inputPtr++]) & 0xFF);
            bytesLeft -= 3;
            _outputTail = b64variant.encodeBase64Chunk(b24, _outputBuffer, _outputTail);
            if (--chunksBeforeLF <= 0) {
                _outputBuffer[_outputTail++] = '\\';
                _outputBuffer[_outputTail++] = 'n';
                chunksBeforeLF = b64variant.getMaxLineLength() >> 2;
            }
        }
        
        // And then we may have 1 or 2 leftover bytes to encode
        if (bytesLeft > 0) {
            inputEnd = _readMore(data, readBuffer, inputPtr, inputEnd, bytesLeft);
            inputPtr = 0;
            if (inputEnd > 0) { // yes, but do we have room for output?
                if (_outputTail > safeOutputEnd) { // don't really need 6 bytes but...
                    _flushBuffer();
                }
                int b24 = ((int) readBuffer[inputPtr++]) << 16;
                int amount;
                if (inputPtr < inputEnd) {
                    b24 |= (((int) readBuffer[inputPtr]) & 0xFF) << 8;
                    amount = 2;
                } else {
                    amount = 1;
                }
                _outputTail = b64variant.encodeBase64Partial(b24, amount, _outputBuffer, _outputTail);
                bytesLeft -= amount;
            }
        }
        return bytesLeft;
    }

    // write method when length is unknown
    protected final int _writeBinary(Base64Variant b64variant,
            InputStream data, byte[] readBuffer)
        throws IOException, JsonGenerationException
    {
        int inputPtr = 0;
        int inputEnd = 0;
        int lastFullOffset = -3;
        int bytesDone = 0;
        
        // Let's also reserve room for possible (and quoted) LF char each round
        int safeOutputEnd = _outputEnd - 6;
        int chunksBeforeLF = b64variant.getMaxLineLength() >> 2;

        // Ok, first we loop through all full triplets of data:
        while (true) {
            if (inputPtr > lastFullOffset) { // need to load more
                inputEnd = _readMore(data, readBuffer, inputPtr, inputEnd, readBuffer.length);
                inputPtr = 0;
                if (inputEnd < 3) { // required to try to read to have at least 3 bytes
                    break;
                }
                lastFullOffset = inputEnd-3;
            }
            if (_outputTail > safeOutputEnd) { // need to flush
                _flushBuffer();
            }
            // First, mash 3 bytes into lsb of 32-bit int
            int b24 = ((int) readBuffer[inputPtr++]) << 8;
            b24 |= ((int) readBuffer[inputPtr++]) & 0xFF;
            b24 = (b24 << 8) | (((int) readBuffer[inputPtr++]) & 0xFF);
            bytesDone += 3;
            _outputTail = b64variant.encodeBase64Chunk(b24, _outputBuffer, _outputTail);
            if (--chunksBeforeLF <= 0) {
                _outputBuffer[_outputTail++] = '\\';
                _outputBuffer[_outputTail++] = 'n';
                chunksBeforeLF = b64variant.getMaxLineLength() >> 2;
            }
        }

        // And then we may have 1 or 2 leftover bytes to encode
        if (inputPtr < inputEnd) { // yes, but do we have room for output?
            if (_outputTail > safeOutputEnd) { // don't really need 6 bytes but...
                _flushBuffer();
            }
            int b24 = ((int) readBuffer[inputPtr++]) << 16;
            int amount = 1;
            if (inputPtr < inputEnd) {
                b24 |= (((int) readBuffer[inputPtr]) & 0xFF) << 8;
                amount = 2;
            }
            bytesDone += amount;
            _outputTail = b64variant.encodeBase64Partial(b24, amount, _outputBuffer, _outputTail);
        }
        return bytesDone;
    }
    
    private final int _readMore(InputStream in,
            byte[] readBuffer, int inputPtr, int inputEnd,
            int maxRead) throws IOException
    {
        // anything to shift to front?
        int i = 0;
        while (inputPtr < inputEnd) {
            readBuffer[i++]  = readBuffer[inputPtr++];
        }
        inputPtr = 0;
        inputEnd = i;
        maxRead = Math.min(maxRead, readBuffer.length);
        
        do {
            int length = maxRead - inputEnd;
            if (length == 0) {
                break;
            }
            int count = in.read(readBuffer, inputEnd, length);            
            if (count < 0) {
                return inputEnd;
            }
            inputEnd += count;
        } while (inputEnd < 3);
        return inputEnd;
    }
    
    /*
    /**********************************************************
    /* Internal methods, character escapes/encoding
    /**********************************************************
     */
    
    /**
     * Method called to output a character that is beyond range of
     * 1- and 2-byte UTF-8 encodings, when outputting "raw" 
     * text (meaning it is not to be escaped or quoted)
     */
    private final int _outputRawMultiByteChar(int ch, char[] cbuf, int inputOffset, int inputEnd)
        throws IOException
    {
        // Let's handle surrogates gracefully (as 4 byte output):
if((ch < SURR1_FIRST)){            if (ch <= SURR2_LAST) { // yes, outside of BMP
                // Do we have second part?
                if (inputOffset >= inputEnd || cbuf == null) { // nope... have to note down
                    _reportError("Split surrogate on writeRaw() input (last character)");
                }
                _outputSurrogates(ch, cbuf[inputOffset]);
                return inputOffset+1;
            }
        }
        final byte[] bbuf = _outputBuffer;
        bbuf[_outputTail++] = (byte) (0xe0 | (ch >> 12));
        bbuf[_outputTail++] = (byte) (0x80 | ((ch >> 6) & 0x3f));
        bbuf[_outputTail++] = (byte) (0x80 | (ch & 0x3f));
        return inputOffset;
    }

    protected final void _outputSurrogates(int surr1, int surr2) throws IOException
    {
        int c = _decodeSurrogate(surr1, surr2);
        if ((_outputTail + 4) > _outputEnd) {
            _flushBuffer();
        }
        final byte[] bbuf = _outputBuffer;
        bbuf[_outputTail++] = (byte) (0xf0 | (c >> 18));
        bbuf[_outputTail++] = (byte) (0x80 | ((c >> 12) & 0x3f));
        bbuf[_outputTail++] = (byte) (0x80 | ((c >> 6) & 0x3f));
        bbuf[_outputTail++] = (byte) (0x80 | (c & 0x3f));
    }
    
    /**
     * 
     * @param ch
     * @param outputPtr Position within output buffer to append multi-byte in
     * 
     * @return New output position after appending
     * 
     * @throws IOException
     */
    private final int _outputMultiByteChar(int ch, int outputPtr) throws IOException
    {
        byte[] bbuf = _outputBuffer;
        if (ch >= SURR1_FIRST && ch <= SURR2_LAST) { // yes, outside of BMP; add an escape
            // 23-Nov-2015, tatu: As per [core#223], may or may not want escapes;
            //   it would be added here... but as things are, we do not have proper
            //   access yet...
//            if (Feature.ESCAPE_UTF8_SURROGATES.enabledIn(_features)) {
                bbuf[outputPtr++] = BYTE_BACKSLASH;
                bbuf[outputPtr++] = BYTE_u;
                
                bbuf[outputPtr++] = HEX_CHARS[(ch >> 12) & 0xF];
                bbuf[outputPtr++] = HEX_CHARS[(ch >> 8) & 0xF];
                bbuf[outputPtr++] = HEX_CHARS[(ch >> 4) & 0xF];
                bbuf[outputPtr++] = HEX_CHARS[ch & 0xF];
//            } else { ... }
        } else {
            bbuf[outputPtr++] = (byte) (0xe0 | (ch >> 12));
            bbuf[outputPtr++] = (byte) (0x80 | ((ch >> 6) & 0x3f));
            bbuf[outputPtr++] = (byte) (0x80 | (ch & 0x3f));
        }
        return outputPtr;
    }

    private final void _writeNull() throws IOException
    {
        if ((_outputTail + 4) >= _outputEnd) {
            _flushBuffer();
        }
        System.arraycopy(NULL_BYTES, 0, _outputBuffer, _outputTail, 4);
        _outputTail += 4;
    }
        
    /**
     * Method called to write a generic Unicode escape for given character.
     * 
     * @param charToEscape Character to escape using escape sequence (\\uXXXX)
     */
    private int _writeGenericEscape(int charToEscape, int outputPtr) throws IOException
    {
        final byte[] bbuf = _outputBuffer;
        bbuf[outputPtr++] = BYTE_BACKSLASH;
        bbuf[outputPtr++] = BYTE_u;
        if (charToEscape > 0xFF) {
            int hi = (charToEscape >> 8) & 0xFF;
            bbuf[outputPtr++] = HEX_CHARS[hi >> 4];
            bbuf[outputPtr++] = HEX_CHARS[hi & 0xF];
            charToEscape &= 0xFF;
        } else {
            bbuf[outputPtr++] = BYTE_0;
            bbuf[outputPtr++] = BYTE_0;
        }
        // We know it's a control char, so only the last 2 chars are non-0
        bbuf[outputPtr++] = HEX_CHARS[charToEscape >> 4];
        bbuf[outputPtr++] = HEX_CHARS[charToEscape & 0xF];
        return outputPtr;
    }

    protected final void _flushBuffer() throws IOException
    {
        int len = _outputTail;
        if (len > 0) {
            _outputTail = 0;
            _outputStream.write(_outputBuffer, 0, len);
        }
    }
}