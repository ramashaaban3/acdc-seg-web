
import { useEffect, useMemo, useState } from "react";
import {
  AppBar,
  Toolbar,
  Typography,
  Container,
  Grid,
  Card,
  CardContent,
  Stack,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  ToggleButtonGroup,
  ToggleButton,
  Chip,
  Box,
  TextField,
  Divider,
} from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";

import { getPatients, askVqa } from "./api";
import MetricCard from "./components/MetricCard";
import OverlayPanel from "./components/OverlayPanel";


const SAMPLE_QUESTIONS = [
  "Bu hastanın EF değeri kaç?",
  "EDV ve ESV değerleri nedir?",
  "Bu sonuçları klinik olarak yorumlar mısın?",
  "Tahmin hatası yüksek mi?",
  "Sol ventrikül dilate mi?",
  "B planı düzeltmesi uygulanmış mı?",
];


function toFixedOrDash(value, ndigits = 2) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  const numberValue = Number(value);

  if (Number.isNaN(numberValue)) {
    return "—";
  }

  return numberValue.toFixed(ndigits);
}


function formatLlmModel(modelName) {
  if (!modelName) {
    return "GPT-4o-mini";
  }

  if (modelName.toLowerCase() === "gpt-4o-mini") {
    return "GPT-4o-mini";
  }

  return modelName;
}


export default function App() {
  const [patients, setPatients] = useState([]);
  const [selected, setSelected] = useState("");

  const [question, setQuestion] = useState(
    "Bu sonuçları klinik olarak yorumlar mısın?"
  );

  const [phase, setPhase] = useState("ED");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [result, setResult] = useState(null);

  const apiBase = import.meta.env.VITE_API_BASE;


  useEffect(() => {
    (async () => {
      try {
        const data = await getPatients();

        setPatients(data);

        if (data?.length) {
          setSelected(
            data[0].real_patient_id || data[0].patient_id
          );
        } else {
          setPatients([
            {
              patient_id: "patient100",
              real_patient_id: "patient100",
            },
          ]);

          setSelected("patient100");
        }
      } catch (e) {
        setError(
          "Backend’e bağlanılamadı. API servisinin çalıştığını kontrol edin."
        );

        setPatients([
          {
            patient_id: "patient100",
            real_patient_id: "patient100",
          },
        ]);

        setSelected("patient100");
      }
    })();
  }, []);


  const selectedId = useMemo(() => {
    const patient = patients.find(
      (item) =>
        item.patient_id === selected ||
        item.real_patient_id === selected
    );

    return patient?.real_patient_id || selected || "";
  }, [patients, selected]);


  function toAbsUrl(url) {
    if (!url) {
      return null;
    }

    if (/^https?:\/\//i.test(url)) {
      return url;
    }

    const base = (apiBase || "").replace(/\/$/, "");
    const path = url.startsWith("/") ? url : `/${url}`;

    return `${base}${path}`;
  }


  async function onAskVqa() {
    setError("");
    setLoading(true);

    try {
      if (!selectedId) {
        throw new Error("Hasta seçilmedi.");
      }

      if (!question.trim()) {
        throw new Error("Lütfen bir soru yazın.");
      }

      const data = await askVqa({
        patientId: selectedId,
        question: question.trim(),

        // Teknik model bilgileri yalnızca backend isteğinde kullanılır.
        // Kullanıcı arayüzünde gösterilmez.
        segmentationModel: "3d_unet",
        llmProvider: "openai",
        llmModel: "gpt-4o-mini",
      });

      console.log("VQA RESPONSE:", data);

      const prediction =
        data?.clinical_metrics?.prediction || {};

      const reference =
        data?.clinical_metrics?.reference || {};

      const errors =
        data?.clinical_metrics?.absolute_errors || {};

      const artifacts =
        data?.artifacts || {};

      const ui =
        data?.ui || {};


      setResult({
        raw: data,

        answer:
          data?.response?.answer || "",

        answerType:
          data?.response?.answer_type ||
          data?.question_type ||
          "",

        confidence:
          data?.response?.confidence || "",

        limitations:
          data?.response?.limitations ||
          ui?.warning ||
          "",

        llmModel:
          formatLlmModel(data?.llm_model),

        edv:
          prediction.edv_ml,

        esv:
          prediction.esv_ml,

        ef:
          prediction.ef_percent,

        refEdv:
          reference.edv_ml,

        refEsv:
          reference.esv_ml,

        refEf:
          reference.ef_percent,

        edvError:
          errors.edv_ml,

        esvError:
          errors.esv_ml,

        efError:
          errors.ef_percent,

        qualityControl:
          data?.quality_control || {},

        phaseInfo:
          data?.phase_info || {},

        edImg:
          toAbsUrl(artifacts.overlay_ed_url),

        esImg:
          toAbsUrl(artifacts.overlay_es_url),
      });
    } catch (e) {
      setError(
        e?.response?.data?.detail ||
          e?.message ||
          "VQA işlemi sırasında bir hata oluştu."
      );
    } finally {
      setLoading(false);
    }
  }


  const year = new Date().getFullYear();

  const barBg =
    "linear-gradient(90deg, rgba(7,12,26,0.96) 0%, rgba(2,34,64,0.94) 45%, rgba(0,120,170,0.92) 100%)";

  const barGlow =
    "0 10px 34px rgba(0,0,0,0.55), 0 0 0 1px rgba(255,255,255,0.08) inset, 0 0 28px rgba(0,190,255,0.18)";


  return (
    <>
      <AppBar
        position="sticky"
        elevation={0}
        sx={{
          borderBottom: 1,
          borderColor: "rgba(255,255,255,0.10)",
          color: "#fff",
          background: barBg,
          backdropFilter: "blur(10px)",
          WebkitBackdropFilter: "blur(10px)",
          boxShadow: barGlow,
          position: "relative",

          "&::after": {
            content: '""',
            position: "absolute",
            left: 0,
            right: 0,
            bottom: 0,
            height: "2px",
            background:
              "linear-gradient(90deg, rgba(0,255,240,0.00), rgba(0,255,240,0.35), rgba(0,190,255,0.45), rgba(0,255,240,0.00))",
          },
        }}
      >
        <Toolbar sx={{ gap: 1.25 }}>
          <Stack>
            <Typography
              variant="h6"
              sx={{
                fontWeight: 800,
                letterSpacing: 0.2,
              }}
            >
              ACDC Cardiac MRI VQA System
            </Typography>

            <Typography
              variant="caption"
              sx={{
                color: "rgba(255,255,255,0.82)",
              }}
            >
              Clinical Metrics • GPT-4o-mini Interpretation • Patient-Based VQA
            </Typography>
          </Stack>
        </Toolbar>
      </AppBar>


      <Box
        component="main"
        sx={{
          flex: "1 0 auto",
        }}
      >
        <Container
          maxWidth="lg"
          sx={{
            py: 4,
          }}
        >
          <Grid container spacing={3}>

            {/* METRIC CARDS */}
            <Grid item xs={12}>
              <Grid
                container
                spacing={2}
                sx={{
                  alignItems: "stretch",
                }}
              >
                <Grid item xs={12} md={4}>
                  <Box sx={{ height: 110 }}>
                    <MetricCard
                      title="EDV"
                      value={toFixedOrDash(result?.edv)}
                      unit={result?.edv != null ? "ml" : ""}
                    />
                  </Box>
                </Grid>

                <Grid item xs={12} md={4}>
                  <Box sx={{ height: 110 }}>
                    <MetricCard
                      title="ESV"
                      value={toFixedOrDash(result?.esv)}
                      unit={result?.esv != null ? "ml" : ""}
                    />
                  </Box>
                </Grid>

                <Grid item xs={12} md={4}>
                  <Box sx={{ height: 110 }}>
                    <MetricCard
                      title="EF"
                      value={toFixedOrDash(result?.ef)}
                      unit={result?.ef != null ? "%" : ""}
                    />
                  </Box>
                </Grid>
              </Grid>
            </Grid>


            {/* LEFT CONTROL PANEL */}
            <Grid item xs={12} md={4}>
              <Card
                variant="outlined"
                sx={{
                  backgroundColor: "rgba(255,255,255,0.88)",
                  backdropFilter: "blur(6px)",
                  WebkitBackdropFilter: "blur(10px)",
                  boxShadow: "0 10px 30px rgba(0,0,0,0.18)",
                  borderColor: "rgba(255,255,255,0.7)",
                }}
              >
                <CardContent>
                  <Stack spacing={2}>
                    <Typography
                      variant="h6"
                      fontWeight={800}
                    >
                      Cardiac MRI VQA Panel
                    </Typography>


                    {/* PATIENT SELECTION */}
                    <FormControl fullWidth>
                      <InputLabel>Hasta</InputLabel>

                      <Select
                        value={selected}
                        label="Hasta"
                        onChange={(e) =>
                          setSelected(e.target.value)
                        }
                      >
                        {patients.map((patient) => (
                          <MenuItem
                            key={
                              patient.real_patient_id ||
                              patient.patient_id
                            }
                            value={
                              patient.real_patient_id ||
                              patient.patient_id
                            }
                          >
                            {patient.patient_id ||
                              patient.real_patient_id}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>


                    {/* FIXED LLM INFORMATION */}
                    <Box
                      sx={{
                        border: "1px solid",
                        borderColor: "divider",
                        borderRadius: 2,
                        px: 1.75,
                        py: 1.15,
                        backgroundColor:
                          "rgba(255,255,255,0.35)",
                      }}
                    >
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{
                          display: "block",
                          mb: 0.25,
                        }}
                      >
                        LLM Model
                      </Typography>

                      <Typography
                        variant="body1"
                        fontWeight={700}
                      >
                        GPT-4o-mini
                      </Typography>
                    </Box>


                    {/* QUESTION */}
                    <TextField
                      label="Klinik soru"
                      multiline
                      minRows={3}
                      value={question}
                      onChange={(e) =>
                        setQuestion(e.target.value)
                      }
                      fullWidth
                      placeholder="Örn: Bu sonuçları klinik olarak yorumlar mısın?"
                    />


                    {/* SAMPLE QUESTIONS */}
                    <Stack spacing={1}>
                      <Typography
                        variant="body2"
                        color="text.secondary"
                      >
                        Örnek sorular
                      </Typography>

                      <Stack
                        direction="row"
                        spacing={1}
                        flexWrap="wrap"
                        useFlexGap
                      >
                        {SAMPLE_QUESTIONS.map(
                          (sampleQuestion) => (
                            <Chip
                              key={sampleQuestion}
                              label={sampleQuestion}
                              size="small"
                              variant="outlined"
                              onClick={() =>
                                setQuestion(sampleQuestion)
                              }
                              sx={{
                                cursor: "pointer",
                              }}
                            />
                          )
                        )}
                      </Stack>
                    </Stack>


                    {/* ASK BUTTON */}
                    <Button
                      size="large"
                      variant="contained"
                      startIcon={
                        loading ? (
                          <CircularProgress size={18} />
                        ) : (
                          <PlayArrowIcon />
                        )
                      }
                      disabled={
                        loading || !selectedId
                      }
                      onClick={onAskVqa}
                    >
                      {loading
                        ? "LLM yanıtlıyor..."
                        : "Ask VQA"}
                    </Button>


                    {error && (
                      <Alert severity="error">
                        {String(error)}
                      </Alert>
                    )}
                  </Stack>
                </CardContent>
              </Card>
            </Grid>


            {/* RIGHT MAIN PANEL */}
            <Grid item xs={12} md={8}>
              <Stack spacing={2}>

                {/* LLM ANSWER PANEL */}
                <Card
                  variant="outlined"
                  sx={{
                    backgroundColor:
                      "rgba(255,255,255,0.88)",
                    backdropFilter: "blur(6px)",
                    WebkitBackdropFilter: "blur(10px)",
                    boxShadow:
                      "0 10px 30px rgba(0,0,0,0.18)",
                    borderColor:
                      "rgba(255,255,255,0.7)",
                  }}
                >
                  <CardContent>
                    <Stack spacing={1.5}>
                      <Stack
                        direction={{
                          xs: "column",
                          sm: "row",
                        }}
                        justifyContent="space-between"
                        spacing={1}
                      >
                        <Typography
                          variant="h6"
                          fontWeight={800}
                        >
                          LLM Clinical Answer
                        </Typography>

                        <Stack
                          direction="row"
                          spacing={1}
                          flexWrap="wrap"
                          useFlexGap
                        >
                          {result?.answerType && (
                            <Chip
                              size="small"
                              label={result.answerType}
                            />
                          )}

                          {result?.confidence && (
                            <Chip
                              size="small"
                              color="primary"
                              label={`confidence: ${result.confidence}`}
                            />
                          )}

                          {result?.llmModel && (
                            <Chip
                              size="small"
                              variant="outlined"
                              label={result.llmModel}
                            />
                          )}
                        </Stack>
                      </Stack>


                      <Typography
                        variant="body1"
                        sx={{
                          minHeight: 72,
                          color: result?.answer
                            ? "text.primary"
                            : "text.secondary",
                          lineHeight: 1.65,
                        }}
                      >
                        {result?.answer ||
                          "LLM cevabı burada görünecek."}
                      </Typography>


                      {result?.limitations && (
                        <Alert severity="warning">
                          {result.limitations}
                        </Alert>
                      )}


                      {result && (
                        <>
                          <Divider />

                          <Grid
                            container
                            spacing={1.5}
                          >
                            <Grid
                              item
                              xs={12}
                              md={4}
                            >
                              <MetricCard
                                title="EDV Error"
                                value={toFixedOrDash(
                                  result.edvError
                                )}
                                unit={
                                  result.edvError != null
                                    ? "ml"
                                    : ""
                                }
                              />
                            </Grid>

                            <Grid
                              item
                              xs={12}
                              md={4}
                            >
                              <MetricCard
                                title="ESV Error"
                                value={toFixedOrDash(
                                  result.esvError
                                )}
                                unit={
                                  result.esvError != null
                                    ? "ml"
                                    : ""
                                }
                              />
                            </Grid>

                            <Grid
                              item
                              xs={12}
                              md={4}
                            >
                              <MetricCard
                                title="EF Error"
                                value={toFixedOrDash(
                                  result.efError
                                )}
                                unit={
                                  result.efError != null
                                    ? "pp"
                                    : ""
                                }
                              />
                            </Grid>
                          </Grid>
                        </>
                      )}
                    </Stack>
                  </CardContent>
                </Card>


                {/* OVERLAY HEADER */}
                <Stack
                  direction="row"
                  justifyContent="space-between"
                  alignItems="center"
                >
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: 1,
                      px: 1.5,
                      py: 0.75,
                      borderRadius: 999,
                      background:
                        "linear-gradient(90deg, rgba(7,12,26,0.55), rgba(0,120,170,0.38))",
                      color: "#fff",
                      backdropFilter: "blur(8px)",
                      WebkitBackdropFilter: "blur(8px)",
                      border:
                        "1px solid rgba(255,255,255,0.10)",
                      boxShadow:
                        "0 10px 26px rgba(0,0,0,0.36), 0 0 18px rgba(0,190,255,0.16)",
                    }}
                  >
                    <Typography
                      variant="h6"
                      sx={{
                        m: 0,
                        fontWeight: 800,
                        color: "#fff",
                      }}
                    >
                      Segmentation Overlay
                    </Typography>

                    <ToggleButtonGroup
                      value={phase}
                      exclusive
                      onChange={(_, value) =>
                        value && setPhase(value)
                      }
                      size="small"
                      sx={{
                        ml: 1,

                        "& .MuiToggleButton-root": {
                          color:
                            "rgba(255,255,255,0.92)",
                          borderColor:
                            "rgba(255,255,255,0.22)",
                          backgroundColor:
                            "rgba(255,255,255,0.10)",
                          px: 1.25,
                        },

                        "& .MuiToggleButton-root:hover": {
                          backgroundColor:
                            "rgba(0,190,255,0.14)",
                          borderColor:
                            "rgba(0,255,240,0.35)",
                        },

                        "& .MuiToggleButton-root.Mui-selected":
                          {
                            color: "#07101a",
                            backgroundColor:
                              "rgba(220,255,252,0.92)",
                            borderColor:
                              "rgba(0,255,240,0.45)",
                            boxShadow:
                              "0 0 0 1px rgba(0,255,240,0.25) inset",
                          },

                        "& .MuiToggleButton-root.Mui-selected:hover":
                          {
                            backgroundColor:
                              "rgba(220,255,252,0.92)",
                          },
                      }}
                    >
                      <ToggleButton value="ED">
                        ED
                      </ToggleButton>

                      <ToggleButton value="ES">
                        ES
                      </ToggleButton>
                    </ToggleButtonGroup>
                  </Box>
                </Stack>


                {/* OVERLAY IMAGE */}
                <Box sx={{ minHeight: 520 }}>
                  <OverlayPanel
                    title={
                      phase === "ED"
                        ? "End-Diastole (ED) Overlay"
                        : "End-Systole (ES) Overlay"
                    }
                    imgUrl={
                      phase === "ED"
                        ? result?.edImg
                        : result?.esImg
                    }
                  />
                </Box>
              </Stack>
            </Grid>
          </Grid>
        </Container>
      </Box>


      {/* FOOTER */}
      <Box
        component="footer"
        sx={{
          mt: "auto",
          borderTop: 1,
          borderColor: "rgba(255,255,255,0.10)",
          color: "rgba(255,255,255,0.90)",
          background: barBg,
          backdropFilter: "blur(10px)",
          WebkitBackdropFilter: "blur(10px)",
          boxShadow:
            "0 -10px 26px rgba(0,0,0,0.38), 0 0 28px rgba(0,190,255,0.14)",
          position: "relative",

          "&::before": {
            content: '""',
            position: "absolute",
            left: 0,
            right: 0,
            top: 0,
            height: "2px",
            background:
              "linear-gradient(90deg, rgba(0,255,240,0.00), rgba(0,255,240,0.28), rgba(0,190,255,0.40), rgba(0,255,240,0.00))",
          },
        }}
      >
        <Container
          maxWidth="lg"
          sx={{
            py: 2.25,
          }}
        >
          <Stack
            direction={{
              xs: "column",
              sm: "row",
            }}
            spacing={1}
            justifyContent="space-between"
            alignItems={{
              xs: "flex-start",
              sm: "center",
            }}
          >
            <Typography
              variant="body2"
              sx={{
                color: "rgba(255,255,255,0.92)",
              }}
            >
              ACDC veri kümesi üzerinde kardiyak MR segmentasyon,
              klinik metrik çıkarımı ve LLM tabanlı VQA için
              geliştirilmiş akademik demo uygulaması.
            </Typography>

            <Typography
              variant="caption"
              sx={{
                color: "rgba(255,255,255,0.72)",
              }}
            >
              {year} • Academic project
            </Typography>
          </Stack>
        </Container>
      </Box>
    </>
  );
}

