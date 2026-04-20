-- Rime Lua filter: puj_filter
-- Generated from scripts/export_rime.py - do not edit manually

local function capitalize_first(text)
    if not text or text == "" then return text end
    return text:gsub("^%l", function(c) return c:upper() end)
end

-- Elegant segmentation using Rime's Phrase components
local function apply_user_separators(cand, env)
    local genuine = cand:get_genuine()
    if not genuine then return cand.text end
    
    -- Defensive check: Only 'phrase' or 'sentence' types usually have components
    if type(genuine.size) ~= "function" or type(genuine.at) ~= "function" then
        return cand.text
    end
    
    local input = env.engine.context.input or ""
    local res = ""
    
    -- Use pcall to safely call Rime C++ methods
    local status, size = pcall(function() return genuine:size() end)
    if not status or size <= 1 then return cand.text end
    
    local parts = {}
    for i = 0, size - 1 do
        local sub_ok, sub = pcall(function() return genuine:at(i) end)
        if not sub_ok or not sub then break end
        
        res = res .. sub.text
        
        if i < size - 1 then
            local next_ok, next_sub = pcall(function() return genuine:at(i + 1) end)
            if next_ok and next_sub then
                -- Extract separator from the gap in the input buffer
                local sep_start = sub._end
                local sep_end = next_sub.start
                if sep_end > sep_start then
                    local sep = input:sub(sep_start + 1, sep_end)
                    res = res .. sep
                end
            end
        end
    end
    
    if res ~= "" then return res end
    return cand.text
end

local function filter(translation, env)
    local input = env.engine.context.input or ""
    
    for cand in translation:iter() do
        local text = cand.text
        local genuine = cand:get_genuine()
        
        -- Remove debug markers and apply logic
        if cand.type == "sentence" or cand.type == "user_phrase" or cand.type == "dictionary" then
            -- Remove any existing debug markers if present (from previous versions)
            text = text:gsub("^⟪[^⟫]*⟫ ", "")
            
            -- For sentence candidates, try to preserve user separators (dashes)
            if cand.type == "sentence" or cand.type == "phrase" then
                text = apply_user_separators(cand, env)
            end
            
            -- Capitalization logic
            if input and input:match("^%u") then
                text = capitalize_first(text)
            end
            
            yield(Candidate(cand.type, cand.start, cand._end, text, cand.comment))
        else
            yield(cand)
        end
    end
end

return filter
