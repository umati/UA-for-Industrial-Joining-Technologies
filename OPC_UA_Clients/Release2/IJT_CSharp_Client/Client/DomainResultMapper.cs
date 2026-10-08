#nullable enable

using System.Globalization;
using IJT_CSharp_Client.Domain.Events;
using IJTBase;
using IJTTightening;
using MachineryResult;
using Opc.Ua;

namespace IJT_CSharp_Client.Client;

/// <summary>
/// Internal integration mapper that converts OPC Foundation SDK types
/// (ResultDataType, JoiningResultDataType, VariantCollection) into SDK-neutral
/// domain representations (ResultEventNotification, DomainResultEnvelope).
/// </summary>
internal static class DomainResultMapper
{
    public static ResultEventNotification MapEvent(
        IDictionary<string, object?> fieldMap,
        ResultDataType? decodedResult = null)
    {
        fieldMap.TryGetValue("Result", out var rawResult);
        var resultDataType = decodedResult;
        if (resultDataType is null && rawResult is not null)
        {
            var raw = rawResult is Variant v ? v.Value : rawResult;
            resultDataType = raw is ExtensionObject eo
                ? eo.Body as ResultDataType
                : raw as ResultDataType;
        }

        var rawPayloadDict = new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase);
        foreach (var kvp in fieldMap)
        {
            if (kvp.Value is not null)
                rawPayloadDict[kvp.Key] = ToSdkNeutral(kvp.Value);
        }

        byte[]? eventIdBytes = null;
        if (fieldMap.TryGetValue("EventId", out var eidObj) && eidObj is not null)
        {
            var rawEid = eidObj is Variant ve ? ve.Value : eidObj;
            if (rawEid is byte[] b) eventIdBytes = b;
            else if (rawEid is string s) eventIdBytes = System.Text.Encoding.UTF8.GetBytes(s);
        }

        DateTime eventTime = DateTime.UtcNow;
        if (fieldMap.TryGetValue("Time", out var tObj) && tObj is not null)
        {
            var rawT = tObj is Variant vt ? vt.Value : tObj;
            if (rawT is DateTime dt) eventTime = dt;
            else if (rawT is DateTimeUtc dtc) eventTime = dtc.ToDateTime();
            else if (rawT is DateTimeOffset dto) eventTime = dto.UtcDateTime;
            else if (DateTime.TryParse(rawT?.ToString(), out var parsed)) eventTime = parsed;
        }

        string eventTypeName = "";
        if (fieldMap.TryGetValue("EventType", out var etObj) && etObj is not null)
        {
            var rawEt = etObj is Variant ve ? ve.Value : etObj;
            eventTypeName = rawEt?.ToString() ?? "";
        }

        string? sourceName = null;
        if (fieldMap.TryGetValue("SourceName", out var snObj) && snObj is not null)
        {
            var rawSn = snObj is Variant vs ? vs.Value : snObj;
            sourceName = rawSn?.ToString();
        }

        string? message = null;
        if (fieldMap.TryGetValue("Message", out var msgObj) && msgObj is not null)
        {
            var rawMsg = msgObj is Variant vm ? vm.Value : msgObj;
            message = rawMsg is LocalizedText lt ? lt.Text : rawMsg?.ToString();
        }

        return new ResultEventNotification
        {
            EventId = eventIdBytes,
            EventTypeName = eventTypeName,
            SourceName = sourceName,
            Message = message,
            EventTime = eventTime,
            ReceivedTime = DateTime.UtcNow,
            Result = MapEnvelope(resultDataType),
            RawPayload = rawPayloadDict,
        };
    }

    public static DomainResultEnvelope? MapEnvelope(ResultDataType? rd)
    {
        if (rd is null) return null;

        var meta = rd.ResultMetaData;
        var jMeta = meta as JoiningResultMetaDataType;

        var unprojected = new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase);
        if (meta is not null)
        {
            if (meta.ResultUri.Count > 0)
                unprojected["ResultUri"] = meta.ResultUri.ToArray();
            if (meta.FileFormat.Count > 0)
                unprojected["FileFormat"] = meta.FileFormat.ToArray();
        }

        var contentItems = new List<DomainResultContentItem>();

        if (rd.ResultContent.Count > 0)
        {
            for (int i = 0; i < rd.ResultContent.Count; i++)
            {
                var item = rd.ResultContent[i];
                var raw = item.Value is ExtensionObject eo ? eo.Body : item.Value;

                if (raw is JoiningResultDataType jr)
                {
                    contentItems.Add(new DomainJoiningResultContentItem(MapSinglePayload(jr)));
                }
                else if (raw is ResultDataType childRd)
                {
                    var mappedChild = MapEnvelope(childRd);
                    if (mappedChild is not null)
                        contentItems.Add(new DomainChildResultContentItem(mappedChild));
                }
                else
                {
                    contentItems.Add(new DomainValueContentItem(item.ToString(), ToSdkNeutral(raw)));
                }
            }
        }

        return new DomainResultEnvelope
        {
            ResultId = meta?.ResultId,
            HasTransferableDataOnFile = meta?.HasTransferableDataOnFile,
            IsPartial = meta?.IsPartial,
            IsSimulated = meta?.IsSimulated,
            ResultState = meta?.ResultState.ToString(),
            StepId = meta?.StepId,
            PartId = meta?.PartId,
            ExternalRecipeId = meta?.ExternalRecipeId,
            InternalRecipeId = meta?.InternalRecipeId,
            ProductId = meta?.ProductId,
            ExternalConfigurationId = meta?.ExternalConfigurationId,
            InternalConfigurationId = meta?.InternalConfigurationId,
            JobId = meta?.JobId,
            CreationTime = meta is not null && meta.CreationTime > DateTime.MinValue ? (DateTime)meta.CreationTime : null,
            ResultEvaluation = meta?.ResultEvaluation.ToString(),
            ResultEvaluationCode = meta?.ResultEvaluationCode != 0 ? meta?.ResultEvaluationCode : null,
            ResultEvaluationDetails = meta is not null ? meta.ResultEvaluationDetails.Text : null,
            ResultUri = meta is not null ? meta.ResultUri.ToArray() ?? [] : [],
            FileFormat = meta is not null ? meta.FileFormat.ToArray() ?? [] : [],

            JoiningTechnology = jMeta is not null ? jMeta.JoiningTechnology.Text : null,
            SequenceNumber = jMeta is not null ? (long)jMeta.SequenceNumber : null,
            Name = jMeta?.Name,
            Description = jMeta is not null ? jMeta.Description.Text : null,
            Classification = jMeta?.Classification,
            ClassificationName = jMeta?.Classification.ToString(),
            OperationMode = jMeta?.OperationMode,
            AssemblyType = jMeta?.AssemblyType.ToString(),
            InterventionType = jMeta?.InterventionType,
            IsGeneratedOffline = jMeta?.IsGeneratedOffline,
            AssociatedEntities = MapEntities(jMeta != null ? jMeta.AssociatedEntities.ToArray() : null),
            ResultCounters = MapCounters(jMeta != null ? jMeta.ResultCounters.ToArray() : null),
            ExtendedMetaData = MapExtendedMeta(jMeta != null ? jMeta.ExtendedMetaData.ToArray() : null),
            ContentItems = contentItems,
            RawPayload = unprojected,
        };
    }

    private static DomainSingleResultPayload MapSinglePayload(JoiningResultDataType jr)
    {
        var mask = (JoiningResultDataTypeFields)jr.EncodingMask;

        var ovs = new List<DomainResultValue>();
        if (jr.OverallResultValues.Count > 0)
        {
            foreach (var rv in jr.OverallResultValues)
            {
                ovs.Add(new DomainResultValue(
                    rv.Name ?? rv.ValueId ?? "?",
                    rv.MeasuredValue,
                    rv.EngineeringUnits?.DisplayName.Text,
                    rv.PhysicalQuantity,
                    rv.ResultEvaluation.ToString()));
            }
        }

        var steps = new List<DomainStepResult>();
        if ((mask & JoiningResultDataTypeFields.StepResults) != 0 && jr.StepResults.Count > 0)
        {
            foreach (var step in jr.StepResults)
            {
                var sValues = new List<DomainResultValue>();
                if (step.StepResultValues.Count > 0)
                {
                    foreach (var rv in step.StepResultValues)
                    {
                        sValues.Add(new DomainResultValue(
                            rv.Name ?? rv.ValueId ?? "?",
                            rv.MeasuredValue,
                            rv.EngineeringUnits?.DisplayName.Text,
                            rv.PhysicalQuantity,
                            rv.ResultEvaluation.ToString()));
                    }
                }
                steps.Add(new DomainStepResult(
                    step.StepResultId,
                    step.Name,
                    step.ResultEvaluation.ToString(),
                    sValues));
            }
        }

        var errors = new List<DomainErrorInfo>();
        if ((mask & JoiningResultDataTypeFields.Errors) != 0 && jr.Errors.Count > 0)
        {
            foreach (var err in jr.Errors)
            {
                errors.Add(new DomainErrorInfo(
                    err.ErrorId,
                    err.ErrorType,
                    err.ErrorMessage.Text,
                    err.LegacyError));
            }
        }

        DomainTraceData? traceData = null;
        if ((mask & JoiningResultDataTypeFields.Trace) != 0 && jr.Trace is not null)
        {
            var stepTraces = new List<DomainStepTrace>();
            if (jr.Trace.StepTraces.Count > 0)
            {
                foreach (var st in jr.Trace.StepTraces)
                {
                    var channels = new List<DomainTraceChannel>();
                    if (st.StepTraceContent.Count > 0)
                    {
                        foreach (var ch in st.StepTraceContent)
                        {
                            channels.Add(new DomainTraceChannel(
                                ch.Name,
                                ch.SensorId,
                                ch.PhysicalQuantity,
                                ch.EngineeringUnits?.DisplayName.Text,
                                ch.Values.ToArray() ?? []));
                        }
                    }
                    stepTraces.Add(new DomainStepTrace(
                        st.StepTraceId,
                        st.StepResultId,
                        st.NumberOfTracePoints,
                        st.SamplingInterval,
                        st.StartTimeOffset,
                        channels));
                }
            }
            traceData = new DomainTraceData(jr.Trace.TraceId, jr.Trace.ResultId, stepTraces);
        }

        return new DomainSingleResultPayload
        {
            FailureReason = (mask & JoiningResultDataTypeFields.FailureReason) != 0 ? jr.FailureReason : null,
            FailingStepResultId = (mask & JoiningResultDataTypeFields.FailingStepResultId) != 0 ? jr.FailingStepResultId : null,
            OverallResultValues = ovs,
            StepResults = steps,
            Errors = errors,
            Trace = traceData,
        };
    }

    private static IReadOnlyList<DomainEntity> MapEntities(IEnumerable<EntityDataType>? entities)
    {
        if (entities is null) return [];
        var list = new List<DomainEntity>();
        foreach (var e in entities)
        {
            list.Add(new DomainEntity(
                e.EntityId ?? "-",
                e.EntityType,
                e.Name,
                e.Description,
                e.EntityOriginId,
                e.IsExternal));
        }
        return list;
    }

    private static IReadOnlyList<DomainCounter> MapCounters(IEnumerable<ResultCounterDataType>? counters)
    {
        if (counters is null) return [];
        var list = new List<DomainCounter>();
        foreach (var c in counters)
        {
            list.Add(new DomainCounter(c.Name ?? "-", c.CounterValue));
        }
        return list;
    }

    private static IReadOnlyDictionary<string, string> MapExtendedMeta(IEnumerable<KeyValueDataType>? kvs)
    {
        if (kvs is null) return new Dictionary<string, string>();
        var dict = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var kv in kvs)
        {
            if (kv.Key is not null)
                dict[kv.Key] = kv.Value.Value?.ToString() ?? kv.Value.ToString();
        }
        return dict;
    }

    /// <summary>
    /// Recursively transforms SDK structures into a structured, best-effort SDK-neutral representation
    /// (dictionaries, lists, primitives, strings) without retaining OPC Foundation SDK references.
    /// Includes reference-cycle detection and error encapsulation.
    /// Intended for logging, diagnostics, and audit; not a bit-level round-trippable wire representation.
    /// </summary>
    public static object? ToSdkNeutral(object? obj, HashSet<object>? visited = null)
    {
        if (obj is null) return null;
        if (obj is Variant v) return ToSdkNeutral(v.Value, visited);

        var type = obj.GetType();
        if (type.IsPrimitive || obj is string || obj is decimal || obj is DateTime || obj is Guid)
            return obj;

        if (type.IsEnum)
        {
            return new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase)
            {
                ["Name"] = Enum.GetName(type, obj) ?? obj.ToString(),
                ["Value"] = Convert.ToInt64(obj)
            };
        }

        if (obj is byte[] bytes)
            return bytes.ToArray();

        if (obj is StatusCode sc)
        {
            return new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase)
            {
                ["Code"] = sc.Code,
                ["Name"] = StatusCode.LookupSymbolicId(sc.Code) ?? sc.ToString()
            };
        }

        if (obj is NodeId nid) return nid.ToString();
        if (obj is ExpandedNodeId enid) return enid.ToString();
        if (obj is QualifiedName qn) return qn.ToString();

        if (obj is LocalizedText lt)
        {
            if (string.IsNullOrEmpty(lt.Locale))
                return lt.Text ?? "";
            return new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase)
            {
                ["Text"] = lt.Text ?? "",
                ["Locale"] = lt.Locale
            };
        }

        if (obj is EUInformation eu)
        {
            return new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase)
            {
                ["NamespaceUri"] = eu.NamespaceUri,
                ["UnitId"] = eu.UnitId,
                ["DisplayName"] = eu.DisplayName.Text,
                ["Description"] = eu.Description.Text
            };
        }

        if (obj is Uuid uuid) return uuid.ToString();

        if (type.IsGenericType && type.Name.StartsWith("ArrayOf", StringComparison.Ordinal))
        {
            var toArrayMethod = type.GetMethod("ToArray");
            if (toArrayMethod is not null)
            {
                var arr = toArrayMethod.Invoke(obj, null) as System.Collections.IEnumerable;
                if (arr is not null)
                {
                    var list = new List<object?>();
                    foreach (var item in arr)
                    {
                        list.Add(ToSdkNeutral(item, visited));
                    }
                    return list;
                }
            }
            return new List<object?>();
        }

        if (type.IsGenericType && type.GetGenericTypeDefinition() == typeof(ReadOnlyMemory<>))
        {
            var toArrayMethod = type.GetMethod("ToArray");
            if (toArrayMethod is not null)
            {
                var arr = toArrayMethod.Invoke(obj, null) as System.Collections.IEnumerable;
                if (arr is not null)
                {
                    var list = new List<object?>();
                    foreach (var item in arr)
                    {
                        list.Add(ToSdkNeutral(item, visited));
                    }
                    return list;
                }
            }
            return new List<object?>();
        }

        if (obj is ExtensionObject eo)
        {
            return new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase)
            {
                ["TypeId"] = eo.TypeId.ToString(),
                ["Encoding"] = eo.Encoding.ToString(),
                ["Body"] = ToSdkNeutral(eo.Body, visited)
            };
        }

        if (type.IsValueType)
        {
            return obj.ToString();
        }

        // Reference cycle guard for all complex reference types (including ExtensionObject, collections, domain models)
        visited ??= new HashSet<object>(System.Collections.Generic.ReferenceEqualityComparer.Instance);
        if (!visited.Add(obj))
        {
            return new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase)
            {
                ["$refCycle"] = true,
                ["$typeName"] = type.FullName
            };
        }

        try
        {
            if (obj is System.Collections.IEnumerable enumerable)
            {
                var list = new List<object?>();
                try
                {
                    foreach (var item in enumerable)
                    {
                        try
                        {
                            list.Add(ToSdkNeutral(item, visited));
                        }
                        catch (Exception itemEx)
                        {
                            list.Add(new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase)
                            {
                                ["$error"] = itemEx.Message,
                                ["$typeName"] = item?.GetType().FullName ?? "null"
                            });
                        }
                    }
                }
                catch (Exception enumEx)
                {
                    list.Add(new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase)
                    {
                        ["$enumerationError"] = enumEx.Message,
                        ["$typeName"] = type.FullName
                    });
                }
                return list;
            }

            var dict = new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase);
            var props = type.GetProperties(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
            foreach (var prop in props)
            {
                if (prop.CanRead && prop.GetIndexParameters().Length == 0 &&
                    prop.Name != "TypeId" && prop.Name != "BinaryEncodingId" &&
                    prop.Name != "XmlEncodingId" && prop.Name != "JsonEncodingId")
                {
                    try
                    {
                        var val = prop.GetValue(obj);
                        if (val is not null)
                            dict[prop.Name] = ToSdkNeutral(val, visited);
                    }
                    catch (Exception propEx)
                    {
                        dict[prop.Name] = new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase)
                        {
                            ["$error"] = propEx.Message,
                            ["$propName"] = prop.Name
                        };
                    }
                }
            }
            return dict;
        }
        catch (Exception ex)
        {
            return new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase)
            {
                ["$error"] = ex.Message,
                ["$typeName"] = type.FullName,
                ["$raw"] = obj.ToString()
            };
        }
        finally
        {
            visited.Remove(obj);
        }
    }
}
