import React from 'react';
import {
  Box,
  FormControl,
  Select,
  MenuItem,
  Button,
  Chip,
  Typography,
  InputLabel,
} from '@mui/material';
import {
  AutoAwesome as SummaryIcon,
  Description as ReportIcon,
  Comment as CommentIcon,
} from '@mui/icons-material';
import { motion } from 'framer-motion';

const ReportSelector = ({ 
  reports, 
  selectedReport, 
  onReportSelect, 
  onGenerateSummary,
  commentsCount 
}) => {
  const handleReportChange = (event) => {
    const reportId = event.target.value;
    const report = reports.find(r => r.id === reportId);
    onReportSelect(reportId);
  };

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, minWidth: 400 }}>
      {/* Report Selector */}
      <FormControl 
        variant="outlined" 
        sx={{ 
          minWidth: 250,
          '& .MuiOutlinedInput-root': {
            background: 'rgba(255, 255, 255, 0.9)',
            backdropFilter: 'blur(10px)',
            '&:hover': {
              background: 'rgba(255, 255, 255, 0.95)',
            },
            '&.Mui-focused': {
              background: 'rgba(255, 255, 255, 1)',
            },
          },
        }}
      >
        <InputLabel id="report-select-label">
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <ReportIcon fontSize="small" />
            Select Report
          </Box>
        </InputLabel>
        <Select
          labelId="report-select-label"
          value={selectedReport?.id || ''}
          onChange={handleReportChange}
          label="Select Report"
          sx={{ 
            borderRadius: 2,
            '& .MuiSelect-select': {
              display: 'flex',
              alignItems: 'center',
              gap: 1,
            },
          }}
        >
          <MenuItem value="">
            <Typography color="text.secondary" sx={{ fontStyle: 'italic' }}>
              Choose a report to review...
            </Typography>
          </MenuItem>
          {reports.map((report) => (
            <MenuItem key={report.id} value={report.id}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                <ReportIcon fontSize="small" color="primary" />
                <Box sx={{ flex: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 500 }}>
                    {report.filename}
                  </Typography>
                  {report.metadata && (
                    <Typography variant="caption" color="text.secondary">
                      {report.metadata.line_count} lines • {Math.round(report.metadata.file_size / 1024)}KB
                    </Typography>
                  )}
                </Box>
              </Box>
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {/* Comments Count Chip */}
      {selectedReport && (
        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.3 }}
        >
          <Chip
            icon={<CommentIcon />}
            label={`${commentsCount} Comments`}
            color={commentsCount > 0 ? 'primary' : 'default'}
            variant={commentsCount > 0 ? 'filled' : 'outlined'}
            sx={{
              background: commentsCount > 0 
                ? 'linear-gradient(135deg, #2563eb 0%, #3b82f6 100%)'
                : 'rgba(255, 255, 255, 0.9)',
              backdropFilter: 'blur(10px)',
              fontWeight: 500,
              '& .MuiChip-icon': {
                color: commentsCount > 0 ? 'white' : 'primary.main',
              },
            }}
          />
        </motion.div>
      )}

      {/* Generate Summary Button */}
      {selectedReport && commentsCount > 0 && (
        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.3, delay: 0.1 }}
        >
          <Button
            variant="contained"
            startIcon={<SummaryIcon />}
            onClick={onGenerateSummary}
            sx={{
              background: 'linear-gradient(135deg, #7c3aed 0%, #8b5cf6 100%)',
              borderRadius: 2,
              px: 3,
              py: 1,
              fontWeight: 600,
              boxShadow: '0 4px 12px rgba(124, 58, 237, 0.3)',
              '&:hover': {
                background: 'linear-gradient(135deg, #6d28d9 0%, #7c3aed 100%)',
                boxShadow: '0 6px 16px rgba(124, 58, 237, 0.4)',
                transform: 'translateY(-1px)',
              },
              transition: 'all 0.2s ease-in-out',
            }}
          >
            Generate Summary
          </Button>
        </motion.div>
      )}
    </Box>
  );
};

export default ReportSelector;