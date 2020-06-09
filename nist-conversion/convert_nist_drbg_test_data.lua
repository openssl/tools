#!/usr/bin/env lua

--[[
A script to convert NIST DRBG test data into a format that evp_test can use.

After unpacking the NIST DRBG test data found at:
    https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Algorithm-Validation-Program/documents/drbg/drbgtestvectors.zip

Each of the nine test files needs to be run through this script.  The files are
three set of three corresponding to the no reseeding, no prediction resistance
and the prediction resistance suites.  Each trio should be processed:

    ./convert_nist_drbg_test_data < CTR_DRBG.rsp >>evprand.txt
    ./convert_nist_drbg_test_data < Hash_DRBG.rsp >>evprand.txt
    ./convert_nist_drbg_test_data mac < HMAC_DRBG.rsp >>evprand.txt

It is advisable to also include title lines between each of the test suites.

--]]

local hname = (arg[1] and arg[1]:find('mac')) and 'HMAC-DRBG' or 'HASH-DRBG'

local state = 'skip'
local index
local remap = {
    ReturnedBits = 'Count',
    EntropyInput = 'Entropy',
    PersonalizationString = 'PersonalisationString',
    ReturnedBits = 'Output',
    EntropyInputPR = 'EntropyPredictionResistance',
    EntropyInputReseed = 'ReseedEntropy',
    AdditionalInputReseed = 'ReseedAdditionalInput',
}

for line in io.lines() do
    line = line:gsub(string.char(13), '')
    if line:len() > 1 and line:sub(1,1) ~= '#' then
        if line:sub(1,1) ==  '[' then
            if state == 'body' or state == 'skip' then
                index = 0
                addin = string.byte('A') - 1
                if line:find 'AES' then
                    state = 'header'
                    print ''
                    print 'RAND = CTR-DRBG'
                    if line:find 'no df' then
                        print 'Availablein = default'
                    end
                    print('Cipher = ' .. line:sub(2):gsub('%s.*', '') .. '-CTR')
                    if line:find 'use df' then
                        print 'DerivationFunction = 1'
                    end
                elseif line:find 'SHA' then
                    state = 'header'
                    print ''
                    print('RAND = ' .. hname)
                    print('Digest = ' .. line:gsub('[][]', ''))
                else
                    state = 'skip'
                end
            end
            if state ~= 'skip' and line:find 'PredictionResistance' then
                print('PredictionResistance = ' .. (line:find('True') and 1 or 0))
            end
            if state ~= 'skip' and line:find 'ReturnedBitsLen' then
                print('GenerateBits = '.. line:sub(20):gsub(']', ''))
            end
        elseif state ~= 'skip' then
            state = 'body'
            local pos = line:find '='
            if pos then
                local k, v = line:gsub('%s*=.*', ''), line:gsub('.*=%s*', '')
                k = remap[k] and remap[k] or k
                if k == 'COUNT' then
                    index = tonumber(v)
                    addin = string.byte('A') - 1
                elseif k == 'AdditionalInput' or k == 'EntropyPredictionResistance' then
                    if k == 'AdditionalInput' then addin = addin + 1 end
                    if v ~= '' then
                        print(string.format('%s%c.%d = %s', k, addin, index, v))
                    end
                elseif v ~= '' then
                    print(string.format('%s.%d = %s', k, index, v))
                end
            end
        end
    end
end
